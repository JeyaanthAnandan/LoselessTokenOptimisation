// Sample order processor — repeated identifiers exercise the rename path.
package com.example.orders;

import java.util.ArrayList;
import java.util.List;

public class OrderProcessor {

    public static class CustomerOrderLineItem {
        public String productIdentifier;
        public int quantityOrdered;
        public int unitPriceInCents;

        public CustomerOrderLineItem(String productIdentifier, int quantityOrdered, int unitPriceInCents) {
            this.productIdentifier = productIdentifier;
            this.quantityOrdered = quantityOrdered;
            this.unitPriceInCents = unitPriceInCents;
        }
    }

    public static int calculateOrderSubtotalInCents(List<CustomerOrderLineItem> customerOrderLineItems) {
        int runningSubtotalInCents = 0;
        for (CustomerOrderLineItem customerOrderLineItem : customerOrderLineItems) {
            runningSubtotalInCents += customerOrderLineItem.quantityOrdered * customerOrderLineItem.unitPriceInCents;
        }
        return runningSubtotalInCents;
    }

    public static List<CustomerOrderLineItem> filterHighValueLineItems(
            List<CustomerOrderLineItem> customerOrderLineItems, int minimumValueInCents) {
        List<CustomerOrderLineItem> highValueLineItems = new ArrayList<>();
        for (CustomerOrderLineItem customerOrderLineItem : customerOrderLineItems) {
            int lineValueInCents = customerOrderLineItem.quantityOrdered * customerOrderLineItem.unitPriceInCents;
            if (lineValueInCents >= minimumValueInCents) {
                highValueLineItems.add(customerOrderLineItem);
            }
        }
        return highValueLineItems;
    }

    public static void main(String[] args) {
        List<CustomerOrderLineItem> customerOrderLineItems = new ArrayList<>();
        customerOrderLineItems.add(new CustomerOrderLineItem("PROD-AAA", 2, 1999));
        customerOrderLineItems.add(new CustomerOrderLineItem("PROD-BBB", 1, 4999));
        customerOrderLineItems.add(new CustomerOrderLineItem("PROD-CCC", 5, 299));
        System.out.println("Subtotal: " + calculateOrderSubtotalInCents(customerOrderLineItems));
        System.out.println(
            "High value: " + filterHighValueLineItems(customerOrderLineItems, 2000).size()
        );
    }
}
