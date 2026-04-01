export function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(value);
}

export function formatValue(value: number | string, unit: string) {
  if (typeof value === "string") {
    return value;
  }
  if (unit === "percent") {
    return `${value.toFixed(1)}%`;
  }
  if (unit === "days") {
    return `${value.toFixed(1)} days`;
  }
  if (unit === "weeks") {
    return value === 0 ? "No shortfall" : `${value} weeks`;
  }
  if (unit === "score") {
    return `${value}/100`;
  }
  return String(value);
}

