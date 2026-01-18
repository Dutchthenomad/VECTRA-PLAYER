/**
 * Dynamic Weighter
 *
 * Modulates prediction confidence based on regime and volatility.
 * Automatically reduces confidence during volatile periods and
 * increases it during predictable suppressed regimes.
 */

class DynamicWeighter {
    /**
     * @param {EquilibriumTracker} equilibriumTracker
     */
    constructor(equilibriumTracker) {
        this.eqTracker = equilibriumTracker;

        // Weight matrices (learned from historical data)
        this.regimeWeights = {
            NORMAL: { final: 0.85, peak: 0.68, duration: 0.84 },
            SUPPRESSED: { final: 0.91, peak: 0.65, duration: 0.87 }, // HIGH confidence
            INFLATED: { final: 0.88, peak: 0.62, duration: 0.82 },
            VOLATILE: { final: 0.62, peak: 0.45, duration: 0.61 }   // LOW confidence
        };
    }

    /**
     * Get dynamic weights for current prediction.
     * @returns {Object} Weights and confidence metrics
     */
    getWeights() {
        const state = this.eqTracker.getState();
        const regime = state.regime;
        const strength = state.regimeStrength;
        const volatility = state.sigma;

        // Base weights from regime
        const baseWeights = { ...this.regimeWeights[regime] };

        // Adjust by regime strength
        if (regime !== 'NORMAL') {
            for (const key of Object.keys(baseWeights)) {
                baseWeights[key] += 0.08 * strength; // Up to 8% boost
            }
        }

        // Volatility penalty
        const volPenalty = Math.max(0, (volatility - 0.0060) / 0.0120);
        for (const key of Object.keys(baseWeights)) {
            baseWeights[key] *= (1.0 - 0.3 * volPenalty); // Up to 30% reduction
        }

        // Clamp weights to reasonable range
        baseWeights.final = Math.max(0.4, Math.min(0.98, baseWeights.final));
        baseWeights.peak = Math.max(0.3, Math.min(0.90, baseWeights.peak));
        baseWeights.duration = Math.max(0.5, Math.min(0.95, baseWeights.duration));

        // Ensemble weight (overall confidence)
        const ensembleWeight = (baseWeights.final + baseWeights.peak + baseWeights.duration) / 3;

        // Outlier sensitivity (higher volatility = more sensitive)
        const outlierSensitivity = 0.5 + 0.5 * volPenalty;

        return {
            finalWeight: baseWeights.final,
            peakWeight: baseWeights.peak,
            durationWeight: baseWeights.duration,
            ensembleWeight,
            outlierSensitivity,
            regime,
            regimeStrength: strength,
            volatility
        };
    }

    /**
     * Get descriptive text for current regime.
     * @returns {string}
     */
    getRegimeDescription() {
        const state = this.eqTracker.getState();
        const strength = (state.regimeStrength * 100).toFixed(0);

        switch (state.regime) {
            case 'SUPPRESSED':
                return `Suppressed (${strength}%) - High predictability, expect mean reversion`;
            case 'INFLATED':
                return `Inflated (${strength}%) - Prices above equilibrium`;
            case 'VOLATILE':
                return `Volatile (${strength}%) - Reduced confidence, expect wider ranges`;
            default:
                return 'Normal - Standard oscillation';
        }
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DynamicWeighter };
}
