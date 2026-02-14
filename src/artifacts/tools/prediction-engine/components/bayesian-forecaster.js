/**
 * Bayesian Forecaster
 *
 * Fuses equilibrium tracker + oscillation model for next-game prediction.
 * Uses simplified Kalman filtering for state estimation.
 * Provides credible intervals (95%) for all predictions.
 */

class BayesianForecaster {
    /**
     * @param {EquilibriumTracker} eqTracker
     * @param {StochasticOscillationModel} oscModel
     * @param {DynamicWeighter} weighter
     */
    constructor(eqTracker, oscModel, weighter) {
        this.eqTracker = eqTracker;
        this.oscModel = oscModel;
        this.weighter = weighter;

        // Simple Kalman state (mean, variance)
        this.kfFinal = { mean: 0.012, variance: 0.0001 };
        this.kfPeak = { mean: 2.2, variance: 1.0 };
        this.kfDuration = { mean: 270, variance: 5000 };

        // Process noise (how much predictions can drift)
        this.qFinal = 0.00001;
        this.qPeak = 0.1;
        this.qDuration = 100;

        // Prediction history for accuracy tracking
        this.predictions = [];
        this.actuals = [];
        this.maxHistory = 100;
    }

    /**
     * Generate forecast for next game.
     * @param {Object} prevGame - Previous game data { final, peak, duration }
     * @returns {Object} Prediction set with intervals and confidence
     */
    forecastNextGame(prevGame) {
        const eqState = this.eqTracker.getState();
        const weights = this.weighter.getWeights();

        // ========== FINAL PRICE PREDICTION ==========

        // Component 1: Mean reversion
        const eqForecast = eqState.muCurrent;
        const reversionSpeed = 0.25 + 0.15 * eqState.regimeStrength;
        const meanReversionComponent = eqForecast + reversionSpeed * (eqForecast - prevGame.final);

        // Component 2: Oscillation pattern (AR model)
        const { point: arForecast, variance: arVariance } = this.oscModel.predictNext();

        // Component 3: Peak effect (high peaks suppress next price)
        const peakEffect = -0.08 * (prevGame.peak - 2.5);

        // Component 4: Duration effect (long games suppress next price)
        const durationEffect = -0.00003 * (prevGame.duration - 250);

        // Weighted combination
        const finalForecast = (
            0.40 * meanReversionComponent +
            0.30 * (eqState.muCurrent + arForecast) +
            0.20 * (eqState.muCurrent + peakEffect) +
            0.10 * (eqState.muCurrent + durationEffect)
        );

        // Variance
        const finalVariance = (
            arVariance +
            eqState.sigma ** 2 * 0.15 +
            (prevGame.peak / 10) ** 2 * 0.01
        );
        const finalSigma = Math.sqrt(Math.max(0.0001, finalVariance));

        // Kalman update for final
        this.kfFinal = this._kalmanPredict(this.kfFinal, this.qFinal);
        const finalForecastKf = this._kalmanUpdate(
            this.kfFinal, finalForecast, finalSigma ** 2
        );

        // ========== PEAK PREDICTION ==========

        // Crash bonus (rewards after crashes)
        let crashBonus = 0.0;
        if (prevGame.final < 0.0080) {
            crashBonus = 3.5;
        } else if (prevGame.final < 0.0100) {
            crashBonus = 2.0;
        }

        // Payout penalty
        let payoutPenalty = 0.0;
        if (prevGame.final > 0.0180) {
            payoutPenalty = 1.5;
        }

        const peakForecast = (
            2.2 +
            crashBonus -
            payoutPenalty -
            0.15 * (prevGame.duration - 250) / 100
        );

        const peakSigma = 1.2 + 0.5 * eqState.regimeStrength;

        this.kfPeak = this._kalmanPredict(this.kfPeak, this.qPeak);
        const peakForecastKf = this._kalmanUpdate(
            this.kfPeak, peakForecast, peakSigma ** 2
        );

        // ========== DURATION PREDICTION ==========

        // Duration inversely related to peak
        let durationForecast = 270 - 80 * (prevGame.peak - 2.5) / 5;

        // Volatility adjustment
        if (eqState.regime === 'VOLATILE') {
            durationForecast += 50;
        }

        const durationSigma = 75 + 50 * eqState.regimeStrength;

        this.kfDuration = this._kalmanPredict(this.kfDuration, this.qDuration);
        const durationForecastKf = this._kalmanUpdate(
            this.kfDuration, durationForecast, durationSigma ** 2
        );

        // ========== BUILD PREDICTION SET ==========

        // 95% credible intervals (2 sigma)
        const prediction = {
            final: {
                point: Math.max(0.001, this.kfFinal.mean),
                ciLower: Math.max(0.001, this.kfFinal.mean - 2 * finalSigma),
                ciUpper: this.kfFinal.mean + 2 * finalSigma,
                sigma: finalSigma,
                confidence: weights.finalWeight
            },
            peak: {
                point: Math.max(1.0, this.kfPeak.mean),
                ciLower: Math.max(0.8, this.kfPeak.mean - 2 * peakSigma),
                ciUpper: this.kfPeak.mean + 2 * peakSigma,
                sigma: peakSigma,
                confidence: weights.peakWeight
            },
            duration: {
                point: Math.round(Math.max(10, this.kfDuration.mean)),
                ciLower: Math.round(Math.max(10, this.kfDuration.mean - 2 * durationSigma)),
                ciUpper: Math.round(this.kfDuration.mean + 2 * durationSigma),
                sigma: durationSigma,
                confidence: weights.durationWeight
            },
            ensembleConfidence: weights.ensembleWeight,
            regime: weights.regime,
            regimeStrength: weights.regimeStrength,
            outlierSensitivity: weights.outlierSensitivity,
            timestamp: Date.now()
        };

        // Store prediction
        this.predictions.push(prediction);
        if (this.predictions.length > this.maxHistory) {
            this.predictions.shift();
        }

        return prediction;
    }

    /**
     * Record actual outcome for accuracy tracking.
     * @param {Object} actual - { final, peak, duration }
     */
    recordActual(actual) {
        this.actuals.push({
            ...actual,
            timestamp: Date.now()
        });
        if (this.actuals.length > this.maxHistory) {
            this.actuals.shift();
        }
    }

    /**
     * Calculate prediction accuracy metrics.
     * @returns {Object} Accuracy metrics
     */
    getAccuracyMetrics() {
        if (this.predictions.length < 2 || this.actuals.length < 2) {
            return { finalMAE: null, peakMAE: null, durationMAE: null, count: 0 };
        }

        // Match predictions to actuals (assumes sequential)
        const n = Math.min(this.predictions.length, this.actuals.length);
        let finalErrors = [];
        let peakErrors = [];
        let durationErrors = [];

        for (let i = 0; i < n - 1; i++) {
            const pred = this.predictions[i];
            const actual = this.actuals[i + 1]; // Next game's actual

            if (pred && actual) {
                finalErrors.push(Math.abs(pred.final.point - actual.final));
                peakErrors.push(Math.abs(pred.peak.point - actual.peak));
                durationErrors.push(Math.abs(pred.duration.point - actual.duration));
            }
        }

        const mean = arr => arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : null;

        return {
            finalMAE: mean(finalErrors),
            peakMAE: mean(peakErrors),
            durationMAE: mean(durationErrors),
            count: finalErrors.length
        };
    }

    /**
     * Reset forecaster state.
     */
    reset() {
        this.kfFinal = { mean: 0.012, variance: 0.0001 };
        this.kfPeak = { mean: 2.2, variance: 1.0 };
        this.kfDuration = { mean: 270, variance: 5000 };
        this.predictions = [];
        this.actuals = [];
    }

    // ===== Kalman Filter Helpers =====

    _kalmanPredict(state, processNoise) {
        return {
            mean: state.mean,
            variance: state.variance + processNoise
        };
    }

    _kalmanUpdate(state, measurement, measurementVariance) {
        const gain = state.variance / (state.variance + measurementVariance);
        state.mean = state.mean + gain * (measurement - state.mean);
        state.variance = (1 - gain) * state.variance;
        return state.mean;
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { BayesianForecaster };
}
