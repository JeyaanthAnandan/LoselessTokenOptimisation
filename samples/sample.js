// Sample shopping cart module — exercises rename of frequently-used identifiers.

class ShoppingCartLineItem {
  constructor(productIdentifier, quantityOrdered, unitPriceInCents) {
    this.productIdentifier = productIdentifier;
    this.quantityOrdered = quantityOrdered;
    this.unitPriceInCents = unitPriceInCents;
  }
}

function calculateShoppingCartSubtotal(shoppingCartLineItems) {
  let runningSubtotalInCents = 0;
  for (const shoppingCartLineItem of shoppingCartLineItems) {
    runningSubtotalInCents +=
      shoppingCartLineItem.quantityOrdered * shoppingCartLineItem.unitPriceInCents;
  }
  return runningSubtotalInCents;
}

function applyPercentageDiscount(shoppingCartLineItems, percentageDiscount) {
  // Mutates each line item's unitPriceInCents by the given percentage.
  for (const shoppingCartLineItem of shoppingCartLineItems) {
    const discountedPriceInCents = Math.floor(
      shoppingCartLineItem.unitPriceInCents * (1 - percentageDiscount / 100)
    );
    shoppingCartLineItem.unitPriceInCents = discountedPriceInCents;
  }
}

function summarizeShoppingCart(shoppingCartLineItems) {
  const runningSubtotalInCents = calculateShoppingCartSubtotal(shoppingCartLineItems);
  return {
    itemCount: shoppingCartLineItems.length,
    subtotalInCents: runningSubtotalInCents,
  };
}

const sampleShoppingCartLineItems = [
  new ShoppingCartLineItem("PROD-AAA", 2, 1999),
  new ShoppingCartLineItem("PROD-BBB", 1, 4999),
  new ShoppingCartLineItem("PROD-CCC", 5, 299),
];

console.log("Subtotal:", calculateShoppingCartSubtotal(sampleShoppingCartLineItems));
applyPercentageDiscount(sampleShoppingCartLineItems, 10);
console.log("After discount:", summarizeShoppingCart(sampleShoppingCartLineItems));
