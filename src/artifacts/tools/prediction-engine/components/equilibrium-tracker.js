/**
 * Equilibrium Tracker
 *
 * Tracks the true equilibrium price and detects regime shifts.
 * Uses exponential weighted moving average (EWMA) for fast adaptation.
 *
 * Regimes:
 * - NORMAL: Standard oscillation around equilibrium
 * - SUPPRESSED: Price pushed below equilibrium (after big payouts)
 * - INFLATED: Price pushed above equilibrium
 * - VOLATILE: High volatility period
 */

class EquilibriumTracker {
    /**
     * @param {Object} options
     * @param {number} [options.lambdaDecay=0.95] - EWMA decay factor (higher = slower adaptation)
     * @param {number} [options.thresholdSigma=2.0] - Regime shift threshold in sigma
     */
    constructor(options = {}) {
        this.lambdaDecay = options.lambdaDecay || 0.95;
        this.thresholdSigma = options.thresholdSigma || 2.0;

        // State variables
        this.mu = 0.0120;           // Current equilibrium estimate
        this.sigma = 0.0060;        // Current volatility estimate
        this.muLongterm = 0.0120;   // Anchor point (slow-moving)

        // Regime tracking
        this.regime = 'NORMAL';     // NORMAL, SUPPRESSED, INFLATED, VOLATILE
        this.regimeStrength = 0.0;  // 0-1, how deep in this regime

        // History for learning
        this.priceHistory = [];
        this.residuals = [];
        this.maxHistory = 200;
    }

    /**
     * Update equilibrium estimates with new game data.
     * @param {number} finalPrice - Final price of completed game
     * @param {number} peak - Peak multiplier reached
     * @param {number} duration - Duration in ticks
     * @returns {Object} Updated state with regime info
     */
    update(finalPrice, peak, duration) {
        // EWMA update for mean
        this.mu = this.lambdaDecay * this.mu + (1 - this.lambdaDecay) * finalPrice;

        // Track residual (deviation from equilibrium)
        const residual = finalPrice - this.muLongterm;
        this.residuals.push(residual);
        if (this.residuals.length > this.maxHistory) {
            this.residuals.shift();
        }

        // EWMA update for volatility (using squared residuals)
        if (this.residuals.length > 1) {
            const recentResiduals = this.residuals.slice(-20);
            const variance = this._variance(recentResiduals);
            this.sigma = this.lambdaDecay * this.sigma + (1 - this.lambdaDecay) * Math.sqrt(variance);
        }

        // ===== REGIME DETECTION =====
        // Guard against near-zero sigma to prevent division instability
        const sigmaSafe = Math.max(this.sigma, 1e-9);
        if (Math.abs(residual) > this.thresholdSigma * sigmaSafe) {
            if (residual < 0) {
                this.regime = 'SUPPRESSED';
                this.regimeStrength = Math.min(1.0, Math.abs(residual) / (this.thresholdSigma * sigmaSafe));
            } else {
                this.regime = 'INFLATED';
                this.regimeStrength = Math.min(1.0, Math.abs(residual) / (this.thresholdSigma * sigmaSafe));
            }
        } else {
            this.regime = 'NORMAL';
            this.regimeStrength = 0.0;
        }

        // ===== VOLATILITY REGIME =====
        if (this.sigma > 0.0085) {
            this.regime = 'VOLATILE';
            // Clamp regimeStrength to [0, 1] range as documented
            this.regimeStrength = Math.min(1.0, Math.max(0.0, (this.sigma - 0.0060) / (0.0120 - 0.0060)));
        }

        // ===== SLOW DRIFT DETECTION =====
        this.priceHistory.push(finalPrice);
        if (this.priceHistory.length > this.maxHistory) {
            this.priceHistory.shift();
        }

        if (this.priceHistory.length > 100) {
            const recentMean = this._mean(this.priceHistory.slice(-30));
            const olderMean = this._mean(this.priceHistory.slice(-100, -70));
            const drift = (recentMean - olderMean) / olderMean;

            // If drift is significant, update anchor
            if (Math.abs(drift) > 0.10) { // 10% shift
                this.muLongterm += 0.01 * drift * this.muLongterm;
            }
        }

        return this.getState();
    }

    /**
     * Get current equilibrium state.
     * @returns {Object}
     */
    getState() {
        const latestResidual = this.residuals.length > 0 ? this.residuals[this.residuals.length - 1] : 0;
        return {
            muCurrent: this.mu,
            muLongterm: this.muLongterm,
            sigma: this.sigma,
            regime: this.regime,
            regimeStrength: this.regimeStrength,
            residual: latestResidual,
            residualZscore: this.sigma > 0 ? latestResidual / this.sigma : 0,
            dataPoints: this.priceHistory.length
        };
    }

    /**
     * Reset tracker to initial state.
     */
    reset() {
        this.mu = 0.0120;
        this.sigma = 0.0060;
        this.muLongterm = 0.0120;
        this.regime = 'NORMAL';
        this.regimeStrength = 0.0;
        this.priceHistory = [];
        this.residuals = [];
    }

    // ===== Helper Functions =====

    _mean(arr) {
        if (arr.length === 0) return 0;
        return arr.reduce((a, b) => a + b, 0) / arr.length;
    }

    _variance(arr) {
        if (arr.length < 2) return 0;
        const m = this._mean(arr);
        return arr.reduce((sum, x) => sum + (x - m) ** 2, 0) / (arr.length - 1);
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EquilibriumTracker };
}
