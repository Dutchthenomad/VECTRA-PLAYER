/**
 * Stochastic Oscillation Model
 *
 * Learns the auto-regressive structure of game data dynamically.
 * Uses online recursive least squares (RLS) for parameter updates.
 * Adapts AR order based on BIC information criterion.
 */

class StochasticOscillationModel {
    /**
     * @param {Object} options
     * @param {number} [options.maxArOrder=5] - Maximum AR order to consider
     * @param {number} [options.lambdaRls=0.98] - RLS forgetting factor (0.95-0.99)
     */
    constructor(options = {}) {
        this.maxArOrder = options.maxArOrder || 5;
        this.arOrder = 3; // Start with AR(3)
        this.lambdaRls = options.lambdaRls || 0.98;

        // AR parameters
        this.arParams = new Array(this.maxArOrder).fill(0);

        // RLS covariance matrix (diagonal approximation for simplicity)
        this.pDiag = new Array(this.maxArOrder).fill(100);

        // Prediction tracking
        this.predictionErrors = [];

        // History
        this.priceResiduals = [];
        this.equilibriumMean = 0.0120;
        this.maxHistory = 100;

        // Update counter
        this.updateCount = 0;
    }

    /**
     * Update model with new game data using RLS.
     * @param {number} price - Final price
     * @param {number} peak - Peak multiplier
     * @param {number} duration - Duration ticks
     * @param {number} [equilibrium=0.012] - Current equilibrium estimate
     */
    updateOnline(price, peak, duration, equilibrium = 0.012) {
        this.equilibriumMean = equilibrium;

        // Use price residuals (deviations from equilibrium)
        const priceResid = price - equilibrium;

        // Only predict if we have enough history
        if (this.priceResiduals.length >= this.arOrder) {
            // Regressor vector [resid[t-1], resid[t-2], ..., resid[t-p]]
            const regressor = this.priceResiduals.slice(-this.arOrder).reverse();

            // RLS prediction
            const prediction = this._dotProduct(this.arParams.slice(0, this.arOrder), regressor);
            const predictionError = priceResid - prediction;
            this.predictionErrors.push(predictionError);

            // Simplified RLS update (diagonal approximation)
            for (let i = 0; i < this.arOrder; i++) {
                // Guard denominator against division by zero
                const denom = this.lambdaRls + this.pDiag[i] * regressor[i] * regressor[i];
                const gain = this.pDiag[i] * regressor[i] / Math.max(denom, 1e-9);
                this.arParams[i] += gain * predictionError;
                // Clamp covariance to prevent negative/zero values (numerical stability)
                const pUpdate = (1 / this.lambdaRls) * (1 - gain * regressor[i]) * this.pDiag[i];
                this.pDiag[i] = Math.max(1e-8, pUpdate);
            }
        }

        // Store residual
        this.priceResiduals.push(priceResid);
        if (this.priceResiduals.length > this.maxHistory) {
            this.priceResiduals.shift();
        }

        // Keep prediction errors bounded
        if (this.predictionErrors.length > this.maxHistory) {
            this.predictionErrors.shift();
        }

        // Adaptive order selection every 50 updates
        this.updateCount++;
        if (this.updateCount % 50 === 0 && this.predictionErrors.length > 50) {
            this._updateArOrder();
        }
    }

    /**
     * Select optimal AR order using BIC.
     * @private
     */
    _updateArOrder() {
        const n = this.predictionErrors.length;
        const errors = this.predictionErrors.slice(-50);
        const mse = this._variance(errors);

        if (mse <= 0) return;

        let bestBic = Infinity;
        let bestOrder = this.arOrder;

        for (let p = 1; p <= this.maxArOrder; p++) {
            // BIC = p * ln(n) + n * ln(mse)
            const bic = p * Math.log(n) + n * Math.log(mse);
            if (bic < bestBic) {
                bestBic = bic;
                bestOrder = p;
            }
        }

        if (bestOrder !== this.arOrder) {
            console.log(`[AR Model] Adaptive order update: p=${bestOrder}`);
            this.arOrder = bestOrder;
        }
    }

    /**
     * Forecast next price residual using learned AR model.
     * @returns {Object} { point: number, variance: number }
     */
    predictNext() {
        if (this.priceResiduals.length < this.arOrder) {
            return { point: 0.0, variance: 0.01 };
        }

        // Regressor from recent residuals
        const regressor = this.priceResiduals.slice(-this.arOrder).reverse();
        const pointForecast = this._dotProduct(this.arParams.slice(0, this.arOrder), regressor);

        // Forecast variance
        const predictionErrorVar = this.predictionErrors.length > 10
            ? this._variance(this.predictionErrors.slice(-50))
            : 0.0001;

        // Parameter uncertainty contribution
        let paramUncertainty = 0;
        for (let i = 0; i < this.arOrder; i++) {
            paramUncertainty += this.pDiag[i] * regressor[i] * regressor[i];
        }

        return {
            point: pointForecast,
            variance: predictionErrorVar + paramUncertainty
        };
    }

    /**
     * Get model diagnostics.
     * @returns {Object}
     */
    getDiagnostics() {
        const recentErrors = this.predictionErrors.slice(-20);
        return {
            arOrder: this.arOrder,
            arParams: this.arParams.slice(0, this.arOrder),
            mse: this._variance(recentErrors),
            dataPoints: this.priceResiduals.length,
            updateCount: this.updateCount
        };
    }

    /**
     * Reset model to initial state.
     */
    reset() {
        this.arParams = new Array(this.maxArOrder).fill(0);
        this.pDiag = new Array(this.maxArOrder).fill(100);
        this.predictionErrors = [];
        this.priceResiduals = [];
        this.updateCount = 0;
        this.arOrder = 3;
    }

    // ===== Helper Functions =====

    _dotProduct(a, b) {
        let sum = 0;
        for (let i = 0; i < Math.min(a.length, b.length); i++) {
            sum += a[i] * b[i];
        }
        return sum;
    }

    _variance(arr) {
        if (arr.length < 2) return 0;
        const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
        return arr.reduce((sum, x) => sum + (x - mean) ** 2, 0) / (arr.length - 1);
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { StochasticOscillationModel };
}
