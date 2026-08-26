/** @odoo-module */

import { ConnectionLostError, rpc, RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentPostProcessing } from '@payment/interactions/post_processing';

const PAYWAY_POLL_INTERVAL_MS = 3000;
const PAYWAY_LIFETIME_MS = 3 * 60 * 1000;

function _toPositiveInt(value, fallback) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

patch(PaymentPostProcessing.prototype, {

    setup() {
        super.setup();
        this.pollPaywayIntervalMs = PAYWAY_POLL_INTERVAL_MS;
        this.pollPaywayLifetimeMs = PAYWAY_LIFETIME_MS;
        this.pollPaywayElapsedMs = 0;
        this.hasLoggedPaywayPollWarning = false;
    },

    start() {
        this._pollPayway();
    },

    _pollPayway() {
        /**
         * ABA PayWay requires a confirmation loop while the payment is still alive.
         * We poll every 3 seconds until the configured lifetime limit (default 3 minutes).
         */
        if (this.pollPaywayElapsedMs >= this.pollPaywayLifetimeMs) {
            return;
        }

        setTimeout(async () => {
            if (this.pollPaywayElapsedMs >= this.pollPaywayLifetimeMs) {
                return;
            }
            this.pollPaywayElapsedMs += this.pollPaywayIntervalMs;

            rpc('/payment/payway/status/poll', {
                'csrf_token': odoo.csrf_token,
            }).then((postProcessingValues) => {
                let { provider_code, state, landing_route } = postProcessingValues;
                if (provider_code === 'aba_payway') {
                    const pollIntervalSeconds = _toPositiveInt(
                        postProcessingValues.poll_interval_seconds,
                        this.pollPaywayIntervalMs / 1000,
                    );
                    const pollLifetimeSeconds = _toPositiveInt(
                        postProcessingValues.poll_lifetime_seconds,
                        this.pollPaywayLifetimeMs / 1000,
                    );
                    this.pollPaywayIntervalMs = pollIntervalSeconds * 1000;
                    this.pollPaywayLifetimeMs = pollLifetimeSeconds * 1000;
                }

                const isFinalState = provider_code != 'aba_payway'
                    || PaymentPostProcessing.getFinalStates(provider_code).has(state)
                    || this.pollPaywayElapsedMs >= this.pollPaywayLifetimeMs;

                if (isFinalState) {
                    if (landing_route && PaymentPostProcessing.getFinalStates(provider_code).has(state)) {
                        window.location = landing_route;
                    }
                    return;
                }
                this._pollPayway();
            }).catch(error => {
                const isRetryError = error instanceof RPCError && error.data?.message === 'retry';
                const isConnectionLostError = error instanceof ConnectionLostError;
                const httpStatus = error instanceof RPCError ? error.data?.httpStatus : undefined;
                const isRetryableHttpError = [429, 500, 502, 503, 504].includes(httpStatus);
                const isRecoverableError = isRetryError || isConnectionLostError || isRetryableHttpError;

                if (isRecoverableError) {
                    this._pollPayway();
                    return;
                }

                if (!this.hasLoggedPaywayPollWarning) {
                    this.hasLoggedPaywayPollWarning = true;
                    console.warn('ABA PayWay poll stopped due to non-recoverable error.', error);
                }
            });

        }, this.pollPaywayIntervalMs);
    }
});