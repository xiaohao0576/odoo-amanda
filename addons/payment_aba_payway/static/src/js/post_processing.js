/** @odoo-module */

import { ConnectionLostError, rpc, RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

import { PaymentPostProcessing } from '@payment/interactions/post_processing';

patch(PaymentPostProcessing.prototype, {

    setup() {
        super.setup();
        this.pollPaywayTimeout = 10000;
    },

    start() {
        super.start(...arguments);
        this._pollPayway();
    },

    _pollPayway() {
        /** 
         * Waiting 10 sec for webhook to completed, if it is not complete.
         * start polling payway payment status every 3 seconds
        */

        setTimeout(async () => {
            rpc('/payment/payway/status/poll', {
                'csrf_token': odoo.csrf_token,

            }).then((postProcessingValues) => {
                let { provider_code, state } = postProcessingValues;
                if (
                    provider_code != 'aba_payway'
                    || PaymentPostProcessing.getFinalStates(provider_code).has(state)
                ) {
                    return;
                }
                else {
                    this.pollPaywayTimeout = 3000;
                    this._pollPayway();
                }
            }).catch(error => {
                const isRetryError = error instanceof RPCError && error.data.message === 'retry';
                const isConnectionLostError = error instanceof ConnectionLostError;
                if (isRetryError || isConnectionLostError) {
                    this.pollPaywayTimeout = 3000;
                    this._pollPayway();
                }
                if (!isRetryError) {
                    throw error;
                }
            });

        }, this.pollPaywayTimeout);
    }
});