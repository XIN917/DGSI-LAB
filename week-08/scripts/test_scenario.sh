#!/bin/bash

# Utility to run commands with nice headers
header() {
    echo -e "\n\033[1;34m=== $1 ===\033[0m"
}

header "1. INITIALIZING DATABASES"
./provider/venv/bin/provider-cli seed
./manufacturer/venv/bin/manufacturer-cli seed
./retailer/venv/bin/retailer-cli init

header "2. RETAILER: CREATING CUSTOMER DEMAND"
./retailer/venv/bin/retailer-cli customer-orders create --sku P3D-Classic --quantity 10
./retailer/venv/bin/retailer-cli purchase-orders create --sku P3D-Classic --quantity 10

header "3. MANUFACTURER: RELEASING TO PRODUCTION"
# Get the ID of the latest pending sales order
ORDER_ID=$(./manufacturer/venv/bin/manufacturer-cli sales orders | grep "pending" | head -n 1 | awk '{print $2}')

if [ -z "$ORDER_ID" ]; then
    echo "No pending orders found (possibly auto-delivered)."
    # Try to find the latest order regardless of status for verification
    ORDER_ID=$(./manufacturer/venv/bin/manufacturer-cli sales orders | head -n 1 | awk '{print $2}')
else
    echo "Releasing Manufacturer Order #$ORDER_ID"
    ./manufacturer/venv/bin/manufacturer-cli production release $ORDER_ID
fi

header "4. SIMULATING 3 DAYS OF PROGRESS"
for i in {1..3}
do
   echo "--- Advancing Day $i ---"
   ./provider/venv/bin/provider-cli day advance
   ./manufacturer/venv/bin/manufacturer-cli day advance
   ./retailer/venv/bin/retailer-cli day advance
done

header "5. FINAL VERIFICATION"
echo "Manufacturer Order Status:"
./manufacturer/venv/bin/manufacturer-cli sales orders | grep "$ORDER_ID"
echo -e "\nRetailer Inventory:"
./retailer/venv/bin/retailer-cli inventory
echo -e "\nRetailer Customer Orders:"
./retailer/venv/bin/retailer-cli customer-orders list
