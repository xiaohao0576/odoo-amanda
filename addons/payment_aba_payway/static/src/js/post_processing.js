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
                const isRetryError = error instanceof RPCError && error.data.message === 'retry';
                const isConnectionLostError = error instanceof ConnectionLostError;
                if (isRetryError || isConnectionLostError) {
                    this._pollPayway();
                }
                if (!isRetryError) {
                    throw error;
                }
            });

        }, this.pollPaywayIntervalMs);
    }
});