"""
Sidebet prediction model using Gradient Boosting

Trains on 14-feature vectors to predict optimal sidebet placement timing.
Target: Win rate >25%, false positive rate <30%
"""

# AUDIT FIX: Lazy import of ML dependencies to avoid crashes in environments without sklearn
# These will be imported when actually needed (in train() or predict() methods)
joblib = None
np = None
GradientBoostingClassifier = None
classification_report = None
confusion_matrix = None
roc_auc_score = None
train_test_split = None
compute_class_weight = None

from .feature_extractor import FEATURE_NAMES


def _ensure_ml_dependencies():
    """Lazy load ML dependencies with clear error message."""
    global joblib, np, GradientBoostingClassifier
    global classification_report, confusion_matrix, roc_auc_score
    global train_test_split, compute_class_weight

    if np is not None:
        return  # Already loaded

    try:
        import joblib as _joblib
        import numpy as _np
        from sklearn.ensemble import GradientBoostingClassifier as _GBC
        from sklearn.metrics import (
            classification_report as _cr,
            confusion_matrix as _cm,
            roc_auc_score as _ras,
        )
        from sklearn.model_selection import train_test_split as _tts
        from sklearn.utils.class_weight import compute_class_weight as _ccw

        joblib = _joblib
        np = _np
        GradientBoostingClassifier = _GBC
        classification_report = _cr
        confusion_matrix = _cm
        roc_auc_score = _ras
        train_test_split = _tts
        compute_class_weight = _ccw
    except ImportError as e:
        raise ImportError(
            f"ML dependencies not installed: {e}\n"
            f"Install with: pip install scikit-learn joblib numpy\n"
            f"Or use: pip install -e '.[ml]' if extras are configured"
        ) from e


class SidebetModel:
    """Gradient Boosting model for sidebet prediction"""

    def __init__(self):
        # AUDIT FIX: Defer model creation until train() is called
        # to avoid importing sklearn at __init__ time
        self.model = None
        self.is_trained = False
        self.optimal_threshold = 0.25  # Default (higher than 0.167 breakeven)

    def _ensure_model(self):
        """Lazy initialize the model."""
        if self.model is None:
            _ensure_ml_dependencies()
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,  # Shallow trees to prevent overfitting
                learning_rate=0.1,
                subsample=0.8,
                min_samples_leaf=20,  # Require decent sample size
                random_state=42,
                verbose=1,
            )

    def train(
        self, X, y, test_size: float = 0.2, val_size: float = 0.25
    ) -> dict:
        """
        Train model on features and labels

        Args:
            X: Feature array of shape (N, 14)
            y: Labels array of shape (N,)
            test_size: Fraction for test set
            val_size: Fraction of remaining for validation set

        Returns:
            Dictionary with training metrics
        """
        # AUDIT FIX: Ensure ML dependencies are loaded before training
        self._ensure_model()

        print(f"\n{'=' * 60}")
        print("SIDEBET MODEL TRAINING")
        print(f"{'=' * 60}")
        print(f"Dataset: {len(X)} samples")
        print(f"Positive rate: {y.mean():.3%}")

        # Handle class imbalance
        class_weights = compute_class_weight("balanced", classes=np.unique(y), y=y)
        print(f"Class weights: {dict(zip([0, 1], class_weights))}")

        # Split: Train/Val/Test (60/20/20)
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_size, random_state=42, stratify=y_temp
        )

        print("\nSplit sizes:")
        print(f"  Train: {len(X_train)} ({len(X_train) / len(X):.1%})")
        print(f"  Val: {len(X_val)} ({len(X_val) / len(X):.1%})")
        print(f"  Test: {len(X_test)} ({len(X_test) / len(X):.1%})")

        # Train model with sample weights for class balance
        sample_weights = np.where(y_train == 1, class_weights[1], class_weights[0])

        print(f"\n{'=' * 60}")
        print("Training model...")
        print(f"{'=' * 60}\n")

        self.model.fit(X_train, y_train, sample_weight=sample_weights)

        self.is_trained = True

        # Evaluate on validation set
        print(f"\n{'=' * 60}")
        print("VALIDATION RESULTS")
        print(f"{'=' * 60}")

        val_pred = self.model.predict(X_val)
        val_pred_proba = self.model.predict_proba(X_val)[:, 1]

        print(classification_report(y_val, val_pred))
        print(f"ROC-AUC: {roc_auc_score(y_val, val_pred_proba):.3f}")

        # Evaluate on test set
        print(f"\n{'=' * 60}")
        print("TEST RESULTS")
        print(f"{'=' * 60}")

        test_pred = self.model.predict(X_test)
        test_pred_proba = self.model.predict_proba(X_test)[:, 1]

        print(classification_report(y_test, test_pred))
        print(f"ROC-AUC: {roc_auc_score(y_test, test_pred_proba):.3f}")

        # Confusion matrix
        cm = confusion_matrix(y_test, test_pred)
        print("\nConfusion Matrix:")
        print("                Predicted")
        print("                No Rug  |  Rug")
        print(f"Actual No Rug:  {cm[0, 0]:6d}  | {cm[0, 1]:6d}")
        print(f"Actual Rug:     {cm[1, 0]:6d}  | {cm[1, 1]:6d}")

        # Feature importance
        print(f"\n{'=' * 60}")
        print("FEATURE IMPORTANCE")
        print(f"{'=' * 60}")

        importances = sorted(
            zip(FEATURE_NAMES, self.model.feature_importances_), key=lambda x: x[1], reverse=True
        )

        for name, importance in importances:
            print(f"{name:25s}: {importance:.4f}")

        # Check if death_spike_score is in top 3
        top_3 = [name for name, _ in importances[:3]]
        if "death_spike_score" in top_3:
            print(f"\n✅ death_spike_score in top 3 (rank #{top_3.index('death_spike_score') + 1})")
        else:
            print("\n⚠️  WARNING: death_spike_score not in top 3!")

        # Threshold analysis (CRITICAL for deployment)
        print(f"\n{'=' * 60}")
        print("THRESHOLD ANALYSIS")
        print(f"{'=' * 60}")

        threshold_results = self.analyze_thresholds(X_test, y_test)

        # Find optimal threshold (highest EV with win rate >25%)
        best_threshold = 0.25
        best_ev = 0

        for result in threshold_results:
            if result["win_rate"] >= 0.25 and result["ev_per_bet"] > best_ev:
                best_threshold = result["threshold"]
                best_ev = result["ev_per_bet"]

        self.optimal_threshold = best_threshold

        print(f"\n✅ Optimal threshold: {self.optimal_threshold:.3f}")
        print(
            f"   Expected win rate: {[r for r in threshold_results if r['threshold'] == best_threshold][0]['win_rate']:.1%}"
        )
        print(f"   Expected EV/bet: {best_ev:.3f}")

        return {
            "train_size": len(X_train),
            "val_size": len(X_val),
            "test_size": len(X_test),
            "val_auc": roc_auc_score(y_val, val_pred_proba),
            "test_auc": roc_auc_score(y_test, test_pred_proba),
            "feature_importances": dict(importances),
            "optimal_threshold": self.optimal_threshold,
            "threshold_results": threshold_results,
        }

    def analyze_thresholds(self, X_test, y_test) -> list[dict]:
        """
        Analyze performance at different probability thresholds

        Critical for finding optimal deployment threshold given 5:1 payout.
        Breakeven at 16.67% win rate.
        """
        # AUDIT FIX: Ensure ML dependencies are loaded
        _ensure_ml_dependencies()

        proba = self.model.predict_proba(X_test)[:, 1]

        results = []

        thresholds = [0.1, 0.167, 0.2, 0.25, 0.3, 0.4, 0.5]

        for threshold in thresholds:
            predictions = (proba >= threshold).astype(int)

            # Calculate metrics
            true_positives = ((predictions == 1) & (y_test == 1)).sum()
            false_positives = ((predictions == 1) & (y_test == 0)).sum()
            false_negatives = ((predictions == 0) & (y_test == 1)).sum()
            total_bets = predictions.sum()

            if total_bets > 0:
                win_rate = true_positives / total_bets
                precision = true_positives / total_bets  # Same as win_rate
                recall = true_positives / (true_positives + false_negatives)

                # Calculate expected value (5:1 payout)
                # Win: +4 units (5-1), Loss: -1 unit
                ev = (true_positives * 4) - false_positives
                ev_per_bet = ev / total_bets if total_bets > 0 else 0

                is_profitable = ev_per_bet > 0
                is_above_target = win_rate >= 0.25

                print(f"\nThreshold: {threshold:.3f}")
                print(f"  Total bets: {total_bets}")
                print(f"  Win rate: {win_rate:.3%} {'✅' if is_above_target else '❌'}")
                print(f"  Precision: {precision:.3%}")
                print(f"  Recall: {recall:.3%}")
                print(f"  EV per bet: {ev_per_bet:+.3f} {'✅' if is_profitable else '❌'}")

                if threshold == 0.167:
                    print("  ^ BREAKEVEN THRESHOLD (16.7% = 1/6)")

                results.append(
                    {
                        "threshold": threshold,
                        "total_bets": total_bets,
                        "win_rate": win_rate,
                        "precision": precision,
                        "recall": recall,
                        "ev_per_bet": ev_per_bet,
                        "is_profitable": is_profitable,
                        "true_positives": true_positives,
                        "false_positives": false_positives,
                    }
                )

        return results

    def predict(self, features) -> tuple[int, float]:
        """
        Make prediction for single sample

        Args:
            features: Feature vector of shape (14,)

        Returns:
            (prediction, probability)
            - prediction: 0 or 1
            - probability: float in [0, 1]
        """
        # AUDIT FIX: Ensure ML dependencies are loaded
        _ensure_ml_dependencies()

        if not self.is_trained:
            raise ValueError("Model not trained yet")

        proba = self.model.predict_proba(features.reshape(1, -1))[0, 1]

        # Use optimal threshold
        prediction = int(proba >= self.optimal_threshold)

        return prediction, proba

    def save(self, filepath: str):
        """Save trained model"""
        # AUDIT FIX: Ensure ML dependencies are loaded
        _ensure_ml_dependencies()

        joblib.dump(
            {
                "model": self.model,
                "optimal_threshold": self.optimal_threshold,
                "is_trained": self.is_trained,
            },
            filepath,
        )
        print(f"\nModel saved to: {filepath}")

    def load(self, filepath: str):
        """Load trained model"""
        # AUDIT FIX: Ensure ML dependencies are loaded
        _ensure_ml_dependencies()

        data = joblib.load(filepath)
        self.model = data["model"]
        self.optimal_threshold = data["optimal_threshold"]
        self.is_trained = data["is_trained"]
        print(f"\nModel loaded from: {filepath}")
        print(f"Optimal threshold: {self.optimal_threshold:.3f}")
