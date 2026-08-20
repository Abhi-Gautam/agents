# Payments incident runbook

If ERROR lines mention CARD_DECLINED_PROVIDER and upstream timeout:
1. Check card-network status page
2. Confirm payments-api version from VERSION file
3. Do not restart pods until provider ACK

Red herring: legacy_retry being false is unrelated to this failure class.
