-- disable aba payway payment provider
UPDATE payment_provider
   SET production_payway_merchant_id = NULL,
       production_payway_key = NULL,
       production_rsa_public_key = NULL,
       sandbox_payway_merchant_id = NULL,
       sandbox_payway_key = NULL,
       sandbox_rsa_public_key = NULL
 WHERE code = 'aba_payway';
