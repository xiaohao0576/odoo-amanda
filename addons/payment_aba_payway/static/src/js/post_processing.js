/** @odoo-module */

import { ConnectionLostError, rpc, RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentPostProcessing } from '@payment/interactions/post_processing';

const PAYWAY_POLL_INTERVAL_MS = 3000;
const PAYWAY_LIFETIME_MS = 3 * 60 * 1000;

patch(PaymentPostProcessing.prototype, {

    setup() {
        super.setup();
        this.pollPaywayIntervalMs = PAYWAY_POLL_INTERVAL_MS;
        this.pollPaywayLifetimeMs = PAYWAY_LIFETIME_MS;
        this.pollPaywayElapsedMs = 0;
        this.hasLoggedPaywayPollWarning = false;
    },

    start() {
        super.start(...arguments);
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
                let { provider_code, state } = postProcessingValues;
                const isFinalState = provider_code != 'aba_payway'
                    || PaymentPostProcessing.getFinalStates(provider_code).has(state)
                    || this.pollPaywayElapsedMs >= this.pollPaywayLifetimeMs;

                if (isFinalState) {
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