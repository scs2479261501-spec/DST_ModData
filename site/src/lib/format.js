const numberFormatter = new Intl.NumberFormat('zh-CN');
const compactFormatter = new Intl.NumberFormat('zh-CN', {
  notation: 'compact',
  maximumFractionDigits: 1,
});
const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return numberFormatter.format(value);
}

export function formatCompact(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return compactFormatter.format(value);
}

export function formatRate(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatPercentValue(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return `${Number(value).toFixed(digits)}%`;
}

export function formatDate(value) {
  if (!value) {
    return '--';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return dateFormatter.format(date);
}

export function formatDays(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return `${formatNumber(value)} 天`;
}

export function formatDecimal(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return Number(value).toFixed(digits);
}
