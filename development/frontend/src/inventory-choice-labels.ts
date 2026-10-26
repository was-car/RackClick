// Entity names are user data. Only closed UI labels are eligible for translation.
export function inventoryEntityOption(value, name) {
 const label = `${name} · ${value}`;
 return { value, label, literal: true, title: label };
}

export function inventoryOptionLabel(option, words) {
 if (option.literal) return option.label;
 const translated = Object.prototype.hasOwnProperty.call(words, option.label) ? words[option.label] : null;
 return typeof translated === 'string' ? translated : option.label;
}
