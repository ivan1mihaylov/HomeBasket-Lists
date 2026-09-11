/**
 * HomeBasket Lists card.
 *
 * Shopping lists that stay in step with the built-in Home Assistant to-do
 * lists, showing what HomeBasket knows about each product. Written against
 * plain DOM APIs on purpose - it uses no Home Assistant frontend internals, so
 * it does not break when those are renamed.
 *
 * https://github.com/ivan1mihaylov/HomeBasket-Lists
 */

const VERSION = '0.8.1';

/* ------------------------------------------------------------------ *
 * Translations
 * ------------------------------------------------------------------ */

const TRANSLATIONS = {
  en: {
    title: 'Lists',
    addPlaceholder: 'Add an item',
    add: 'Add',
    empty: 'Nothing on this list yet.',
    noLists: 'No list yet. Add one under Settings → Devices & Services → HomeBasket Lists.',
    notSetUp:
      'HomeBasket Lists is not set up yet. Add it under Settings → Devices & ' +
      'Services → Add Integration → HomeBasket Lists, then reload this page.',
    noAnswer: 'HomeBasket Lists did not answer.',
    tryAgain: 'Try again',
    done: 'Done',
    doneCount: (n) => `${n} done`,
    itemsLeft: (n) => `${n} left`,
    edit: 'Edit item',
    name: 'Name',
    quantity: 'Quantity',
    unit: 'Unit',
    unitHint: 'Free text — pieces, kg, litres, whatever fits.',
    defaultUnit: 'pcs',
    countedUp: (name, count) => `${name}: ${count} now`,
    alreadyThere: (name) => `${name} is already on the list`,
    less: 'One less',
    more: 'One more',
    suggestionsHint: 'Not on the list — tap to add',
    openProduct: 'Known to HomeBasket',
    type: 'Type',
    store: 'Shop',
    note: 'Note',
    anywhere: 'Anywhere',
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    deleteTitle: 'Delete item',
    deleteMessage: (name) => `${name} will be removed from this list and every linked one.`,
    sync: 'Sync now',
    syncing: 'Syncing…',
    synced: 'Lists are in step',
    linkedTo: (n) => `Linked to ${n} list${n === 1 ? '' : 's'}`,
    suggestions: 'Known products',
    searchFailed: (reason) => `Suggestions failed: ${reason}`,
    searchUnavailable:
      'Suggestions cannot reach HomeBasket Lists. Restart Home Assistant if you ' +
      'have just updated it.',
    cardVersion: (version) => `Card version ${version}`,
    product: 'Product',
    due: 'Due',
    duration: 'Takes',
    tools: 'Tools',
    toolsHint: 'Optional. What the job needs — a drill, a ladder, a spare filter.',
    units: { minutes: 'minutes', hours: 'hours', days: 'days' },
    shortUnits: { minutes: 'min', hours: 'h', days: 'd' },
    types: { '': 'None', product: 'Product', task: 'Task' },
    details: 'Product details',
    loading: 'Loading…',
    noDetails: 'HomeBasket has nothing more on this product.',
    close: 'Close',
    photo: 'Photo',
    takePhoto: 'Take or upload a photo',
    removePhoto: 'Remove the photo',
    photoTooBig: 'That image could not be read.',
    openOnOff: 'Open Food Facts page',
    sectionNutrition: 'Nutrition, per 100 g',
    sectionIngredients: 'Ingredients',
    sectionAbout: 'About',
    fieldBrand: 'Brand',
    fieldQuantity: 'Quantity',
    fieldCategories: 'Categories',
    fieldLabels: 'Labels',
    fieldAllergens: 'Allergens',
    fieldPackaging: 'Packaging',
    fieldOrigins: 'Origin',
    fieldStores: 'Shops',
    fieldCountries: 'Sold in',
    fieldBarcodes: 'Barcodes',
    nutriScore: 'Nutri-Score',
    novaGroup: 'NOVA',
    ecoScore: 'Eco-Score',
    novaExplained: { 1: 'Unprocessed', 2: 'Culinary ingredient', 3: 'Processed', 4: 'Ultra-processed' },
    nutriments: {
      'energy-kcal': 'Energy',
      fat: 'Fat',
      'saturated-fat': 'of which saturates',
      carbohydrates: 'Carbohydrates',
      sugars: 'of which sugars',
      fiber: 'Fibre',
      proteins: 'Protein',
      salt: 'Salt',
    },
  },
  bg: {
    title: 'Списъци',
    addPlaceholder: 'Добави запис',
    add: 'Добави',
    empty: 'В този списък още няма нищо.',
    noLists: 'Още няма списък. Добави от Настройки → Устройства и услуги → HomeBasket Lists.',
    notSetUp:
      'HomeBasket Lists още не е добавена. Добави я от Настройки → Устройства ' +
      'и услуги → Добавяне на интеграция → HomeBasket Lists и презареди страницата.',
    noAnswer: 'HomeBasket Lists не отговори.',
    tryAgain: 'Опитай пак',
    done: 'Готови',
    doneCount: (n) => `${n} готови`,
    itemsLeft: (n) => `остават ${n}`,
    edit: 'Редакция на запис',
    name: 'Име',
    quantity: 'Количество',
    unit: 'Мерна единица',
    unitHint: 'Свободен текст — бр., кг, литра, каквото пасва.',
    defaultUnit: 'бр.',
    countedUp: (name, count) => `${name}: станаха ${count}`,
    alreadyThere: (name) => `${name} вече е в списъка`,
    less: 'С едно по-малко',
    more: 'С едно повече',
    suggestionsHint: 'Не са в списъка — натисни, за да добавиш',
    openProduct: 'Познат на HomeBasket',
    type: 'Тип',
    store: 'Магазин',
    note: 'Бележка',
    anywhere: 'Навсякъде',
    save: 'Запази',
    cancel: 'Отказ',
    delete: 'Изтрий',
    deleteTitle: 'Изтриване на запис',
    deleteMessage: (name) => `${name} ще бъде премахнат от този списък и от всички свързани.`,
    sync: 'Синхронизирай',
    syncing: 'Синхронизиране…',
    synced: 'Списъците са изравнени',
    linkedTo: (n) => `Свързан с ${n} ${n === 1 ? 'списък' : 'списъка'}`,
    suggestions: 'Познати продукти',
    searchFailed: (reason) => `Предложенията не успяха: ${reason}`,
    searchUnavailable:
      'Предложенията не стигат до HomeBasket Lists. Рестартирай Home Assistant, ' +
      'ако току-що си обновявал.',
    cardVersion: (version) => `Версия на картата ${version}`,
    product: 'Продукт',
    due: 'Срок',
    duration: 'Отнема',
    tools: 'Инструменти',
    toolsHint: 'По избор. Какво трябва за работата — бормашина, стълба, филтър.',
    units: { minutes: 'минути', hours: 'часа', days: 'дни' },
    shortUnits: { minutes: 'мин', hours: 'ч', days: 'дни' },
    types: { '': 'Без', product: 'Продукт', task: 'Задача' },
    details: 'Информация за продукта',
    loading: 'Зареждане…',
    noDetails: 'HomeBasket няма повече информация за този продукт.',
    close: 'Затвори',
    photo: 'Снимка',
    takePhoto: 'Снимай или качи снимка',
    removePhoto: 'Премахни снимката',
    photoTooBig: 'Изображението не можа да се прочете.',
    openOnOff: 'Страница в Open Food Facts',
    sectionNutrition: 'Хранителни стойности, на 100 г',
    sectionIngredients: 'Съставки',
    sectionAbout: 'За продукта',
    fieldBrand: 'Марка',
    fieldQuantity: 'Количество',
    fieldCategories: 'Категории',
    fieldLabels: 'Етикети',
    fieldAllergens: 'Алергени',
    fieldPackaging: 'Опаковка',
    fieldOrigins: 'Произход',
    fieldStores: 'Магазини',
    fieldCountries: 'Продава се в',
    fieldBarcodes: 'Баркодове',
    nutriScore: 'Nutri-Score',
    novaGroup: 'NOVA',
    ecoScore: 'Eco-Score',
    novaExplained: { 1: 'Непреработена', 2: 'Кулинарна съставка', 3: 'Преработена', 4: 'Ултрапреработена' },
    nutriments: {
      'energy-kcal': 'Енергийна стойност',
      fat: 'Мазнини',
      'saturated-fat': 'от които наситени',
      carbohydrates: 'Въглехидрати',
      sugars: 'от които захари',
      fiber: 'Влакнини',
      proteins: 'Белтъчини',
      salt: 'Сол',
    },
  },
};

function stringsFor(language) {
  const code = String(language || 'en').toLowerCase().split('-')[0];
  return TRANSLATIONS[code] || TRANSLATIONS.en;
}

/* ------------------------------------------------------------------ *
 * Styles
 * ------------------------------------------------------------------ */

const STYLES = `
  :host {
    --hb-fg: var(--primary-text-color, #212121);
    --hb-muted: var(--secondary-text-color, #727272);
    --hb-accent: var(--primary-color, #03a9f4);
    --hb-danger: var(--error-color, #db4437);
    --hb-ok: var(--success-color, #43a047);
    --hb-line: var(--divider-color, rgba(127, 127, 127, 0.22));
    --hb-surface: var(--card-background-color, #fff);
    --hb-sunken: color-mix(in srgb, var(--hb-fg) 5%, transparent);
    --hb-raised: color-mix(in srgb, var(--hb-fg) 3%, var(--hb-surface));
    display: block;
    color: var(--hb-fg);
  }

  .card {
    background: var(--hb-surface);
    border-radius: var(--ha-card-border-radius, 22px);
    box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.1));
    border: var(--ha-card-border-width, 1px) solid
      var(--ha-card-border-color, var(--hb-line));
    overflow: hidden;
  }

  header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 18px 8px; }
  header h2 { margin: 0; font-size: 1.3rem; font-weight: 600; line-height: 1.2; }
  header .right { display: flex; align-items: center; gap: 6px; }
  .pill {
    padding: 5px 12px;
    border-radius: 999px;
    background: var(--hb-sunken);
    color: var(--hb-muted);
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
  }

  .tabs { display: flex; gap: 6px; overflow-x: auto; padding: 4px 18px 0; scrollbar-width: none; }
  .tabs::-webkit-scrollbar { display: none; }
  .tab {
    flex: 0 0 auto;
    padding: 7px 14px;
    border-radius: 999px;
    border: 1px solid var(--hb-line);
    background: var(--hb-raised);
    font-size: 0.875rem;
    white-space: nowrap;
  }
  .tab[aria-selected='true'] {
    background: var(--hb-accent);
    border-color: var(--hb-accent);
    color: var(--text-primary-color, #fff);
    font-weight: 600;
  }

  .body { padding: 12px 18px 18px; }

  button { font: inherit; color: inherit; background: none; border: none; cursor: pointer; border-radius: 10px; }
  button:disabled { opacity: 0.45; cursor: default; }
  button svg { width: 20px; height: 20px; fill: currentColor; display: block; }
  .icon-btn { display: grid; place-items: center; width: 36px; height: 36px; color: var(--hb-muted); }
  .icon-btn:hover { color: var(--hb-accent); background: var(--hb-sunken); }
  .icon-btn.danger:hover { color: var(--hb-danger); }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 9px 14px;
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    background: var(--hb-surface);
    font-size: 0.875rem;
    white-space: nowrap;
  }
  .btn.primary { background: var(--hb-accent); border-color: var(--hb-accent); color: var(--text-primary-color, #fff); }
  .btn.block { width: 100%; }

  .add-row { display: flex; gap: 8px; margin-bottom: 14px; }
  .add-row input {
    flex: 1 1 auto;
    min-width: 0;
    box-sizing: border-box;
    font: inherit;
    font-size: 0.95rem;
    color: var(--hb-fg);
    background: var(--hb-sunken);
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    padding: 11px 14px;
  }
  .add-row input:focus { outline: 2px solid var(--hb-accent); outline-offset: -1px; }
  .add-row .btn.primary { padding: 0 16px; }

  /* What is being typed, matched against the products HomeBasket knows. */
  .suggest { margin: -6px 0 14px; }
  .suggest .heading {
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--hb-muted);
    padding: 8px 2px 6px;
  }
  .suggest .heading .sub {
    display: block;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    font-size: 0.6875rem;
    padding-top: 2px;
  }
  /* Dashed and tinted, so a suggestion cannot be mistaken for a row that is
     already on the list. */
  .suggest .option {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    box-sizing: border-box;
    padding: 8px 10px;
    margin-bottom: 6px;
    border: 1px dashed color-mix(in srgb, var(--hb-accent) 55%, var(--hb-line));
    border-radius: 12px;
    background: color-mix(in srgb, var(--hb-accent) 7%, transparent);
    text-align: start;
  }
  .suggest .option:hover,
  .suggest .option[aria-selected='true'] {
    border-style: solid;
    border-color: var(--hb-accent);
    background: color-mix(in srgb, var(--hb-accent) 16%, transparent);
  }
  .suggest .option .add-hint {
    flex: 0 0 auto;
    color: var(--hb-accent);
    font-size: 1.1rem;
    font-weight: 600;
  }
  .suggest .option .thumb { width: 34px; height: 34px; border-radius: 9px; }
  .suggest .option .thumb svg { width: 17px; height: 17px; }
  .suggest .option .who { flex: 1 1 auto; min-width: 0; }
  .suggest .option .who .name { font-size: 0.875rem; font-weight: 600; overflow-wrap: anywhere; }
  .suggest .option .who .meta { font-size: 0.6875rem; color: var(--hb-muted); }

  .items { display: flex; flex-direction: column; gap: 8px; }
  .item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 14px;
    border: 1px solid var(--hb-line);
    background: var(--hb-raised);
  }
  .item.done { opacity: 0.55; }
  .item.done .name { text-decoration: line-through; }

  .tick {
    flex: 0 0 auto;
    width: 24px;
    height: 24px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    border: 2px solid var(--hb-line);
    color: transparent;
    padding: 0;
  }
  .tick:hover { border-color: var(--hb-accent); }
  .tick[aria-pressed='true'] { background: var(--hb-ok); border-color: var(--hb-ok); color: #fff; }
  .tick svg { width: 14px; height: 14px; }

  .thumb {
    flex: 0 0 auto;
    width: 42px;
    height: 42px;
    border-radius: 10px;
    background: var(--hb-sunken);
    display: grid;
    place-items: center;
    overflow: hidden;
  }
  .thumb img { width: 100%; height: 100%; object-fit: cover; }
  .thumb svg { width: 20px; height: 20px; fill: var(--hb-muted); }

  .who { flex: 1 1 auto; min-width: 0; cursor: pointer; }
  .who .name { font-size: 0.9375rem; font-weight: 600; line-height: 1.3; overflow-wrap: anywhere; }
  .who .meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 3px; }
  .chip {
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--hb-sunken);
    color: var(--hb-muted);
    font-size: 0.6875rem;
    font-weight: 500;
    white-space: nowrap;
  }
  .chip.store { background: color-mix(in srgb, var(--hb-accent) 16%, transparent); color: var(--hb-accent); }
  .chip.qty { font-variant-numeric: tabular-nums; }

  .group-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 18px 0 8px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--hb-muted);
  }
  .group-title::after { content: ''; flex: 1 1 auto; height: 1px; background: var(--hb-line); }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 26px 8px;
    text-align: center;
    color: var(--hb-muted);
    font-size: 0.875rem;
  }
  .empty p { margin: 0; max-width: 40ch; }

  /* Dialogs */
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.55);
  }
  .dialog {
    width: min(440px, 100%);
    max-height: min(90vh, 760px);
    display: flex;
    flex-direction: column;
    background: var(--hb-surface);
    color: var(--hb-fg);
    border-radius: 18px;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.35);
  }
  .dialog h3 { margin: 0; padding: 18px 18px 8px; font-size: 1.1rem; font-weight: 600; }
  .dialog .content { padding: 8px 18px 16px; overflow: auto; }
  .dialog label { display: block; margin-bottom: 6px; font-size: 0.8125rem; color: var(--hb-muted); }
  .dialog input[type='text'],
  .dialog select,
  .dialog textarea {
    width: 100%;
    box-sizing: border-box;
    font: inherit;
    font-size: 1rem;
    color: var(--hb-fg);
    background: var(--hb-sunken);
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    padding: 11px 13px;
    margin-bottom: 14px;
  }

  /* The chevron is ours, so it sits beside the text instead of against the
     far edge, and looks the same on every platform. */
  .dialog select,
  .editor select {
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%239b9b9b'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    background-size: 22px 22px;
    padding-inline-end: 38px;
  }
  .dialog textarea { min-height: 74px; resize: vertical; }

  /* A photo of the item itself, for what HomeBasket has no picture of. */
  /* At the top of the sheet, in the middle of it. */
  .photo-top { text-align: center; }
  .photo-top label { display: block; }
  .photo-box {
    position: relative;
    width: 124px;
    height: 124px;
    margin: 0 auto 16px;
  }
  .photo-add {
    width: 100%;
    height: 100%;
    display: grid;
    place-items: center;
    border: 1px dashed var(--hb-line);
    border-radius: 18px;
    background: var(--hb-sunken);
    color: var(--hb-muted);
    cursor: pointer;
  }
  .photo-add:hover { color: var(--hb-accent); border-color: var(--hb-accent); }
  .photo-add svg { width: 34px; height: 34px; fill: currentColor; }
  .photo-preview {
    width: 100%;
    height: 100%;
    border-radius: 18px;
    overflow: hidden;
    background: var(--hb-sunken);
  }
  .photo-preview img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .photo-remove {
    position: absolute;
    top: -9px;
    right: -9px;
    width: 30px;
    height: 30px;
    display: grid;
    place-items: center;
    border: 0;
    border-radius: 50%;
    background: var(--hb-danger);
    color: #fff;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
    cursor: pointer;
  }
  .photo-remove svg { width: 17px; height: 17px; fill: currentColor; }
  .dialog input[type='file'] { display: none; }
  .dialog .actions { display: flex; justify-content: flex-end; gap: 8px; padding: 6px 18px 18px; }
  .dialog .hint { font-size: 0.8125rem; color: var(--hb-muted); margin: 0 0 12px; }
  .stepper { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
  .stepper .step {
    flex: 0 0 auto;
    width: 40px;
    height: 42px;
    display: grid;
    place-items: center;
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    background: var(--hb-sunken);
    font-size: 1.25rem;
    line-height: 1;
  }
  .stepper .step:hover { border-color: var(--hb-accent); color: var(--hb-accent); }
  /* Scoped through .dialog so these beat the standalone field rules, which
     would otherwise keep their bottom margin and knock the row out of line. */
  .dialog .stepper input[type='number'] {
    flex: 1 1 auto;
    min-width: 0;
    margin-bottom: 0;
    text-align: center;
  }
  .dialog .stepper input[type='text'] {
    flex: 1 1 40%;
    min-width: 0;
    margin-bottom: 0;
  }

  /* The same idea on a list row, as text rather than a badge. */
  .amount { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8125rem; }
  .amount .step {
    width: 22px;
    height: 22px;
    display: grid;
    place-items: center;
    border-radius: 6px;
    border: 1px solid var(--hb-line);
    color: var(--hb-muted);
    font-size: 0.9375rem;
    line-height: 1;
    padding: 0;
  }
  .amount .step:hover { border-color: var(--hb-accent); color: var(--hb-accent); }
  .amount .value { font-variant-numeric: tabular-nums; font-weight: 600; }
  .amount .unit { color: var(--hb-muted); }

  .dialog .duration { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
  .dialog .duration input[type='number'] { flex: 1 1 auto; min-width: 0; margin-bottom: 0; }
  .dialog .duration select { flex: 0 0 auto; width: 42%; margin-bottom: 0; }
  .dialog input[type='number'] {
    width: 100%;
    box-sizing: border-box;
    font: inherit;
    font-size: 1rem;
    color: var(--hb-fg);
    background: var(--hb-sunken);
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    padding: 11px 13px;
    margin-bottom: 14px;
  }
  .dialog input[type='date'] {
    width: 100%;
    box-sizing: border-box;
    font: inherit;
    font-size: 1rem;
    color: var(--hb-fg);
    background: var(--hb-sunken);
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    padding: 11px 13px;
    margin-bottom: 14px;
  }
  .dialog .product-note {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    margin-bottom: 14px;
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    background: var(--hb-sunken);
    font-size: 0.8125rem;
    text-align: start;
    cursor: pointer;
  }
  .dialog .product-note:hover { border-color: var(--hb-accent); }
  .dialog .product-note .thumb { width: 36px; height: 36px; border-radius: 9px; }
  .dialog .product-note .who { flex: 1 1 auto; min-width: 0; }
  .dialog .product-note .who div:first-child { font-weight: 600; overflow-wrap: anywhere; }
  .dialog .product-note .chevron { flex: 0 0 auto; color: var(--hb-muted); font-size: 1.1rem; }

  /* Product details */
  .dialog.wide { width: min(560px, 100%); }
  .details h4 {
    margin: 18px 0 8px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--hb-muted);
  }
  .details p { margin: 0; font-size: 0.875rem; line-height: 1.5; }
  .details-head { display: flex; gap: 14px; margin-bottom: 16px; }
  .details-head .shot {
    flex: 0 0 auto;
    width: 88px;
    height: 88px;
    border-radius: 16px;
    overflow: hidden;
    background: var(--hb-sunken);
    display: grid;
    place-items: center;
  }
  .details-head .shot img { width: 100%; height: 100%; object-fit: contain; }
  .details-head .shot svg { width: 26px; height: 26px; fill: var(--hb-muted); }
  .details-head .who { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
  .details-head .who .name { font-size: 1.05rem; font-weight: 600; line-height: 1.25; }
  .details-head .who .sub { font-size: 0.8125rem; color: var(--hb-muted); }

  .grades { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 6px; }
  .grade { display: flex; align-items: center; gap: 8px; padding: 7px 12px 7px 8px; border-radius: 12px; background: var(--hb-sunken); }
  .grade .letter {
    width: 26px;
    height: 26px;
    display: grid;
    place-items: center;
    border-radius: 8px;
    color: #fff;
    font-weight: 700;
    font-size: 0.875rem;
    text-transform: uppercase;
  }
  .grade .letter.a { background: #038141; }
  .grade .letter.b { background: #85bb2f; color: #10240b; }
  .grade .letter.c { background: #fecb02; color: #3b2f00; }
  .grade .letter.d { background: #ee8100; }
  .grade .letter.e { background: #e63e11; }
  .grade .letter.n1 { background: #00a24d; }
  .grade .letter.n2 { background: #ffc832; color: #3b2f00; }
  .grade .letter.n3 { background: #ff8714; }
  .grade .letter.n4 { background: #e63e11; }
  .grade .meaning { display: flex; flex-direction: column; line-height: 1.2; }
  .grade .meaning b { font-size: 0.75rem; font-weight: 600; }
  .grade .meaning span { font-size: 0.6875rem; color: var(--hb-muted); }

  .facts { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  .facts td { padding: 7px 0; border-bottom: 1px solid var(--hb-line); }
  .facts tr:last-child td { border-bottom: none; }
  .facts td + td { text-align: end; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .facts .indent { padding-inline-start: 14px; color: var(--hb-muted); }

  .about { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; font-size: 0.875rem; }
  .about dt { color: var(--hb-muted); }
  .about dd { margin: 0; overflow-wrap: anywhere; }

  .details .source {
    margin-top: 20px;
    padding-top: 14px;
    border-top: 1px solid var(--hb-line);
    font-size: 0.75rem;
  }
  .details .source a { color: var(--hb-accent); }

  .toast {
    position: fixed;
    left: 50%;
    bottom: 24px;
    transform: translateX(-50%);
    z-index: 20;
    max-width: min(90vw, 420px);
    padding: 12px 16px;
    border-radius: 12px;
    background: #323232;
    color: #fff;
    font-size: 0.875rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
  .toast.error { background: var(--hb-danger); }

  /* Editor */
  .editor { display: flex; flex-direction: column; gap: 16px; padding: 8px 0; }
  .editor .field { display: flex; flex-direction: column; gap: 6px; }
  .editor .field > span { font-size: 0.8125rem; color: var(--hb-muted); }
  .editor .field small { font-size: 0.75rem; color: var(--hb-muted); }
  .editor input[type='text'], .editor select {
    width: 100%;
    box-sizing: border-box;
    font: inherit;
    font-size: 1rem;
    color: var(--hb-fg);
    background: var(--hb-sunken);
    border: 1px solid var(--hb-line);
    border-radius: 12px;
    padding: 10px 12px;
  }
  .editor .toggle { display: flex; align-items: center; gap: 12px; font-size: 0.9375rem; cursor: pointer; }
  .editor .toggle input { flex: 0 0 auto; width: 20px; height: 20px; margin: 0; accent-color: var(--hb-accent); }
`;

/* ------------------------------------------------------------------ *
 * DOM helpers
 * ------------------------------------------------------------------ */

const SVG_NS = 'http://www.w3.org/2000/svg';

/**
 * Read a picked file and return it as a downscaled JPEG data URL.
 *
 * Phone cameras produce multi-megabyte images; the list only ever shows a
 * thumbnail, so shrinking before upload keeps the stored photos small.
 */
function readPhoto(file, maxSize = 320) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('unreadable'));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error('unreadable'));
      image.onload = () => {
        const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', 0.82));
      };
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

const ICONS = {
  check: 'M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
  plus: 'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
  sync: 'M12 4V1L8 5l4 4V6a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8z',
  image:
    'M21 3H3a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm0 16H3l4.5-6 3 4L14 13l7 6z',
  task: 'M19 3h-4.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm-7 0a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm-2 14-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z',
  camera:
    'M4 4h3l2-2h6l2 2h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm8 3a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6z',
  close: 'M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z',
  trash:
    'M9 3v1H4v2h1v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6h1V4h-5V3H9zm2 5h2v10h-2V8zm-4 0h2v10H7V8zm8 0h2v10h-2V8z',
};

function icon(name) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('d', ICONS[name] || '');
  svg.appendChild(path);
  return svg;
}

function el(tag, options = {}, ...children) {
  const node = document.createElement(tag);
  const { class: className, text, on, ...attrs } = options;
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    node.setAttribute(key, value === true ? '' : String(value));
  }
  for (const [event, handler] of Object.entries(on || {})) {
    node.addEventListener(event, handler);
  }
  node.append(...children.filter(Boolean));
  return node;
}

function gradeBadge(tone, letter, label, meaning) {
  return el(
    'div',
    { class: 'grade' },
    el('span', { class: `letter ${tone}`, text: letter }),
    el(
      'span',
      { class: 'meaning' },
      el('b', { text: label }),
      meaning ? el('span', { text: meaning }) : null,
    ),
  );
}

function iconButton(name, label, onClick, extraClass = '') {
  return el(
    'button',
    {
      class: `icon-btn ${extraClass}`.trim(),
      title: label,
      'aria-label': label,
      on: { click: onClick },
    },
    icon(name),
  );
}

function openDialog(root, { title, build, buttons, wide }) {
  const backdrop = el('div', { class: 'backdrop' });
  const dialog = el('div', {
    class: wide ? 'dialog wide' : 'dialog',
    role: 'dialog',
    'aria-modal': 'true',
  });
  const content = el('div', { class: 'content' });
  const actions = el('div', { class: 'actions' });

  const close = () => {
    document.removeEventListener('keydown', onKey);
    backdrop.remove();
  };
  const onKey = (event) => {
    if (event.key === 'Escape') close();
  };

  backdrop.addEventListener('click', (event) => {
    if (event.target === backdrop) close();
  });
  document.addEventListener('keydown', onKey);

  dialog.append(el('h3', { text: title }), content, actions);
  backdrop.appendChild(dialog);
  build(content, close);

  for (const { label, primary, start, onClick } of buttons) {
    const button = el('button', {
      class: primary ? 'btn primary' : 'btn',
      text: label,
      on: { click: () => onClick(close) },
    });
    if (start) button.style.marginInlineEnd = 'auto';
    actions.appendChild(button);
  }

  root.appendChild(backdrop);
  content.querySelector('input[type="text"]')?.focus();
  return close;
}

function confirmDialog(root, t, { title, message }) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (result, close) => {
      if (settled) return;
      settled = true;
      resolve(result);
      close();
    };
    openDialog(root, {
      title,
      build: (content) => content.appendChild(el('p', { class: 'hint', text: message })),
      buttons: [
        { label: t.cancel, onClick: (close) => finish(false, close) },
        { label: t.delete, primary: true, onClick: (close) => finish(true, close) },
      ],
    });
  });
}

function toast(root, message, isError = false) {
  root.querySelector('.toast')?.remove();
  const node = el('div', { class: isError ? 'toast error' : 'toast', text: message });
  root.appendChild(node);
  setTimeout(() => node.remove(), isError ? 5000 : 3000);
}

/* ------------------------------------------------------------------ *
 * The card
 * ------------------------------------------------------------------ */

const DEFAULT_CONFIG = {
  title: null,
  language: null,
  list: null,
  show_completed: true,
  group_by_store: true,
};

const STATUS_DONE = 'completed';
const STATUS_OPEN = 'needs_action';

// Three kinds, and each shows only what it needs: a product is bought
// somewhere in some amount, a task takes time and tools, and something with no
// type at all is just a line with a note.
const TYPE_PRODUCT = 'product';
const TYPE_TASK = 'task';
const TYPES = ['', TYPE_PRODUCT, TYPE_TASK];
const DURATION_UNITS = ['minutes', 'hours', 'days'];

const isTask = (type) => type === TYPE_TASK;
const isProduct = (type) => type === TYPE_PRODUCT;

class HomeBasketListsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = { ...DEFAULT_CONFIG };
    this._lists = [];
    this._selected = null;
    this._photos = new Map();
    this._loadingPhotos = new Set();
    this._busy = false;
    this._suggestions = [];
    this._suggestIndex = -1;
    this._suggestTimer = null;
    this._unsubscribe = null;
    this._rendered = false;
  }

  static getConfigElement() {
    return document.createElement('homebasket-lists-card-editor');
  }

  static getStubConfig() {
    return { type: 'custom:homebasket-lists-card' };
  }

  setConfig(config) {
    this._config = { ...DEFAULT_CONFIG, ...config };
    if (this._rendered) this._render();
  }

  getCardSize() {
    return 8;
  }

  get _t() {
    return stringsFor(this._config.language || this._hass?.locale?.language);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._build();
      this._connect();
    }
  }

  connectedCallback() {
    if (this._hass && !this._unsubscribe) this._connect();
  }

  disconnectedCallback() {
    this._unsubscribe?.then((off) => off());
    this._unsubscribe = null;
  }

  /* ---------------- Backend ---------------- */

  async _call(type, payload = {}) {
    return this._hass.connection.sendMessagePromise({ type, ...payload });
  }

  async _connect() {
    await this._refresh();
    this._unsubscribe = this._hass.connection.subscribeEvents(
      () => this._refresh(),
      'homebasket_lists_updated',
    );
  }

  async _refresh() {
    try {
      const { lists } = await this._call('homebasket_lists/lists');
      this._lists = lists || [];
      this._error = null;

      // Keep the chosen list if it is still there, otherwise fall back.
      const wanted = this._config.list;
      const match = wanted
        ? this._lists.find(
            (board) => board.entry_id === wanted || board.name === wanted,
          )
        : null;
      const current = this._lists.find((board) => board.entry_id === this._selected);
      this._selected = (match || current || this._lists[0])?.entry_id || null;
    } catch (err) {
      this._error =
        err?.code === 'unknown_command' ? this._t.notSetUp : err?.message || this._t.noAnswer;
    }
    this._render();
  }

  get _board() {
    return this._lists.find((board) => board.entry_id === this._selected) || null;
  }

  /* ---------------- Actions ---------------- */

  async _addItem(summary, extra = {}) {
    const text = (summary || '').trim();
    if (!text || !this._board || this._busy) return;

    this._busy = true;
    this._input.disabled = true;
    this._clearSuggestions();
    try {
      // A line added here is something to buy, one of, unless the list is
      // fixed to another kind or the caller says otherwise.
      const fixed = this._fixedType();
      const kind = fixed === null ? TYPE_PRODUCT : fixed;
      const result = await this._call('homebasket_lists/item/add', {
        entry_id: this._board.entry_id,
        summary: text,
        item_type: kind || null,
        ...(isProduct(kind) ? { quantity: 1, unit: this._t.defaultUnit } : {}),
        ...extra,
      });
      // Adding something the list already has does whatever the list says -
      // count it, keep it, or write a second line - and silence would look
      // like nothing happened at all.
      const item = result?.item || {};
      if (result?.outcome === 'counted') {
        toast(this.shadowRoot, this._t.countedUp(item.summary || text, item.quantity ?? ''));
      } else if (result?.outcome === 'kept') {
        toast(this.shadowRoot, this._t.alreadyThere(item.summary || text));
      }
      this._input.value = '';
    } catch (err) {
      toast(this.shadowRoot, err.message || this._t.noAnswer, true);
    } finally {
      this._busy = false;
      this._input.disabled = false;
      await this._refresh();
      this._input.focus();
    }
  }

  /* ---------------- Suggestions while typing ---------------- */

  /**
   * Offer the products HomeBasket knows as you type.
   *
   * Picking one takes its name and links the item to it, so it lands on the
   * list already knowing its picture, category and details - no waiting for a
   * name to match exactly.
   */
  _onTyping(text) {
    clearTimeout(this._suggestTimer);
    const query = (text || '').trim();

    // No products to offer without HomeBasket, so do not go asking.
    if (this._board && this._board.products_available === false) {
      this._clearSuggestions();
      return;
    }

    // One or two letters match half the shelf; below that it is just noise.
    if (query.length < 2) {
      this._clearSuggestions();
      return;
    }

    // Each request gets a number, and only the newest one may paint. Comparing
    // the field's text instead threw away a good answer whenever a phone
    // keyboard adjusted the word after the request went out.
    const ticket = (this._suggestTicket = (this._suggestTicket || 0) + 1);

    this._suggestTimer = setTimeout(async () => {
      try {
        const { products } = await this._call('homebasket_lists/products/search', {
          query,
        });
        if (ticket !== this._suggestTicket) return;
        this._suggestions = products || [];
      } catch (err) {
        if (ticket !== this._suggestTicket) return;
        this._suggestions = [];

        // Swallowing this made a broken search look exactly like a search that
        // found nothing. There is no console on a phone, so it has to be said
        // on screen - once, so it does not nag with every keystroke.
        console.warn('homebasket-lists: product search failed', err);
        if (!this._warnedAboutSearch) {
          this._warnedAboutSearch = true;
          const t = this._t;
          toast(
            this.shadowRoot,
            err?.code === 'unknown_command'
              ? t.searchUnavailable
              : t.searchFailed(err?.message || err?.code || 'unknown'),
            true,
          );
        }
      }
      this._suggestIndex = -1;
      this._renderSuggestions();
    }, 180);
  }

  _clearSuggestions() {
    clearTimeout(this._suggestTimer);
    this._suggestions = [];
    this._suggestIndex = -1;
    this._renderSuggestions();
  }

  /** Arrow keys walk the list; Enter takes the highlighted one. */
  _onSuggestKey(event) {
    if (!this._suggestions.length) return false;

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const step = event.key === 'ArrowDown' ? 1 : -1;
      // The cycle runs through every suggestion and back to what was typed,
      // so it has one more state than there are suggestions.
      const states = this._suggestions.length + 1;
      this._suggestIndex =
        ((this._suggestIndex + 1 + step + states) % states) - 1;
      this._renderSuggestions();
      return true;
    }

    if (event.key === 'Escape') {
      this._clearSuggestions();
      return true;
    }

    if (event.key === 'Enter' && this._suggestIndex >= 0) {
      event.preventDefault();
      this._pickSuggestion(this._suggestions[this._suggestIndex]);
      return true;
    }
    return false;
  }

  _pickSuggestion(product) {
    if (!product) return;
    this._addItem(product.name, { product_code: product.code });
  }

  _renderSuggestions() {
    if (!this._suggestBox) return;

    if (!this._suggestions.length) {
      this._suggestBox.replaceChildren();
      return;
    }

    const t = this._t;
    const box = el(
      'div',
      {},
      el(
        'div',
        { class: 'heading' },
        el('span', { text: t.suggestions }),
        el('span', { class: 'sub', text: t.suggestionsHint }),
      ),
    );

    for (const [index, product] of this._suggestions.entries()) {
      const thumb = el('div', { class: 'thumb' });
      const image = el('img', { alt: '', hidden: true });
      thumb.append(image, icon('image'));
      if (product.has_photo) this._fillPhoto(product.code, image);
      else if (product.image) {
        image.src = product.image;
        image.hidden = false;
      }

      box.appendChild(
        el(
          'button',
          {
            class: 'option',
            'aria-selected': String(index === this._suggestIndex),
            on: {
              // Before blur, so the field losing focus cannot cancel the pick.
              pointerdown: (event) => {
                event.preventDefault();
                this._pickSuggestion(product);
              },
            },
          },
          thumb,
          el(
            'div',
            { class: 'who' },
            el('div', { class: 'name', text: product.name }),
            el('div', {
              class: 'meta',
              text: [product.brand, product.category].filter(Boolean).join(' · '),
            }),
          ),
          el('span', { class: 'add-hint', text: '+' }),
        ),
      );
    }

    this._suggestBox.replaceChildren(box);
  }

  async _toggle(item) {
    try {
      await this._call('homebasket_lists/item/update', {
        entry_id: this._board.entry_id,
        uid: item.uid,
        status: item.status === STATUS_DONE ? STATUS_OPEN : STATUS_DONE,
      });
    } catch (err) {
      toast(this.shadowRoot, err.message || this._t.noAnswer, true);
    }
    await this._refresh();
  }

  async _remove(item) {
    const t = this._t;
    const confirmed = await confirmDialog(this.shadowRoot, t, {
      title: t.deleteTitle,
      message: t.deleteMessage(item.summary),
    });
    if (!confirmed) return;
    try {
      await this._call('homebasket_lists/item/remove', {
        entry_id: this._board.entry_id,
        uid: item.uid,
      });
    } catch (err) {
      toast(this.shadowRoot, err.message || this._t.noAnswer, true);
    }
    await this._refresh();
  }

  async _sync() {
    const t = this._t;
    toast(this.shadowRoot, t.syncing);
    try {
      await this._call('homebasket_lists/sync', { entry_id: this._board.entry_id });
      toast(this.shadowRoot, t.synced);
    } catch (err) {
      toast(this.shadowRoot, err.message || t.noAnswer, true);
    }
    await this._refresh();
  }

  /** Fetch the photo of an item itself and hand it to an <img>. */
  _fillItemPhoto(item, image) {
    const key = `item:${item.uid}`;
    if (this._photos.has(key)) {
      image.src = this._photos.get(key);
      image.hidden = false;
      return;
    }
    if (this._loadingPhotos.has(key)) return;

    this._loadingPhotos.add(key);
    this._call('homebasket_lists/item/photo/get', {
      entry_id: this._board.entry_id,
      uid: item.uid,
    })
      .then(({ photo }) => {
        if (!photo) return;
        this._photos.set(key, photo);
        image.src = photo;
        image.hidden = false;
      })
      .catch(() => {})
      .finally(() => this._loadingPhotos.delete(key));
  }

  /** Fetch a product photo held by HomeBasket and hand it to an <img>. */
  _fillPhoto(code, image) {
    if (this._photos.has(code)) {
      image.src = this._photos.get(code);
      image.hidden = false;
      return;
    }
    if (this._loadingPhotos.has(code)) return;

    this._loadingPhotos.add(code);
    this._call('homebasket_lists/product/photo', { code })
      .then(({ photo }) => {
        if (!photo) return;
        this._photos.set(code, photo);
        image.src = photo;
        image.hidden = false;
      })
      .catch(() => {})
      .finally(() => this._loadingPhotos.delete(code));
  }

  /* ---------------- Names ---------------- */

  _storeName(entityId) {
    if (!entityId) return null;
    return this._hass?.states?.[entityId]?.attributes?.friendly_name || entityId;
  }

  _typeName(type) {
    return this._t.types[type || ''] ?? type;
  }

  /** The kinds this list allows. Both, unless its settings say otherwise. */
  _allowedTypes() {
    const kinds = TYPES.slice(1);
    const allowed = this._board?.item_types;
    if (!Array.isArray(allowed)) return kinds;
    return kinds.filter((kind) => allowed.includes(kind));
  }

  /**
   * The kind every item on this list must have, or null when each item
   * decides for itself. A list fixed to one kind does not show the field at
   * all - the integration would only set it back.
   */
  _fixedType() {
    const allowed = this._allowedTypes();
    if (allowed.length === 1) return allowed[0];
    if (!allowed.length) return '';
    return null;
  }

  /** "30 min", "2 h" - what a task takes, in the unit it was given in. */
  _durationLabel(item) {
    if (!item.duration) return null;
    const unit = this._t.shortUnits[item.duration_unit] || item.duration_unit || '';
    return `${item.duration} ${unit}`.trim();
  }

  /* ---------------- The item sheet ---------------- */

  async _openItem(item) {
    const t = this._t;
    const board = this._board;

    const saved = await new Promise((resolve) => {
      let settled = false;
      const fields = {};
      let type = item.type || '';
      // The photo is not written until Save, like every other field here.
      let photoData = null;
      let photoTouched = false;
      let drawPhoto = () => {};
      const finish = (value, close) => {
        if (settled) return;
        settled = true;
        resolve(value);
        close();
      };

      openDialog(this.shadowRoot, {
        title: t.edit,
        build: (content) => {
          // What HomeBasket knows, if anything. Tapping it opens the rest.
          if (item.product) {
            const thumb = el('div', { class: 'thumb' });
            const image = el('img', { alt: '', hidden: true });
            thumb.append(image, icon('image'));
            if (item.product.has_photo) this._fillPhoto(item.product.code, image);
            else if (item.product.image) {
              image.src = item.product.image;
              image.hidden = false;
            }
            content.appendChild(
              el(
                'button',
                {
                  class: 'product-note',
                  on: { click: () => this._openProductDetails(item.product) },
                },
                thumb,
                el(
                  'div',
                  { class: 'who' },
                  el('div', { text: item.product.name }),
                  el('div', { class: 'hint', text: t.openProduct }),
                ),
                el('span', { class: 'chevron', text: '›' }),
              ),
            );
          }

          // A product HomeBasket knows brings its own picture; everything
          // else - a task, a loose vegetable, a part from the hardware shop -
          // can have one of its own.
          if (!item.product) {
            const file = el('input', {
              type: 'file',
              accept: 'image/*',
              capture: 'environment',
            });
            file.addEventListener('change', async () => {
              const [picked] = file.files || [];
              if (!picked) return;
              try {
                photoData = await readPhoto(picked);
                photoTouched = true;
                drawPhoto();
              } catch {
                toast(this.shadowRoot, t.photoTooBig, true);
              }
              file.value = '';
            });

            // Either the square button or the picture in its place, never both.
            const box = el('div', { class: 'photo-box' });
            drawPhoto = () => {
              if (!photoData) {
                box.replaceChildren(
                  el(
                    'button',
                    {
                      class: 'photo-add',
                      title: t.takePhoto,
                      'aria-label': t.takePhoto,
                      on: { click: () => file.click() },
                    },
                    icon('camera'),
                  ),
                );
                return;
              }
              box.replaceChildren(
                el('div', { class: 'photo-preview' }, el('img', { src: photoData, alt: '' })),
                el(
                  'button',
                  {
                    class: 'photo-remove',
                    title: t.removePhoto,
                    'aria-label': t.removePhoto,
                    on: {
                      click: () => {
                        photoData = null;
                        photoTouched = true;
                        drawPhoto();
                      },
                    },
                  },
                  icon('close'),
                ),
              );
            };
            drawPhoto();

            // A stored photo arrives afterwards; redraw once it is here.
            if (item.has_photo) {
              this._call('homebasket_lists/item/photo/get', {
                entry_id: board.entry_id,
                uid: item.uid,
              })
                .then(({ photo }) => {
                  if (!photo || photoTouched) return;
                  this._photos.set(`item:${item.uid}`, photo);
                  photoData = photo;
                  drawPhoto();
                })
                .catch(() => {});
            }

            content.appendChild(
              el('div', { class: 'photo-top' }, el('label', { text: t.photo }), box, file),
            );
          }

          content.appendChild(el('label', { text: t.name }));
          fields.summary = el('input', { type: 'text', value: item.summary || '' });
          content.appendChild(fields.summary);


          const fixed = this._fixedType();
          if (fixed === null) {
            content.appendChild(el('label', { text: t.type }));
            fields.type = el('select');
            for (const name of TYPES) {
              fields.type.appendChild(
                el('option', { value: name, text: this._typeName(name) }),
              );
            }
            fields.type.value = type;
            content.appendChild(fields.type);
          } else {
            // Nothing to choose: the list gives every item this kind, so the
            // sheet shows the fields that kind needs and nothing else.
            type = fixed;
            fields.type = { value: fixed };
          }

          const perType = el('div');
          content.appendChild(perType);

          const drawPerType = () => {
            perType.replaceChildren();
            fields.quantity = null;
            fields.unit = null;
            fields.store = null;
            fields.due = null;
            fields.duration = null;
            fields.durationUnit = null;
            fields.tools = null;

            if (isProduct(type)) {
              perType.appendChild(el('label', { text: t.quantity }));
              fields.quantity = el('input', {
                type: 'number',
                min: '0',
                step: 'any',
                inputmode: 'decimal',
                value: item.quantity ?? '',
              });
              const nudge = (by) => {
                const next = Math.max(0, (Number(fields.quantity.value) || 0) + by);
                fields.quantity.value = next ? String(next) : '';
              };
              fields.unit = el('input', {
                type: 'text',
                placeholder: t.unit,
                value: item.unit || '',
              });
              perType.appendChild(
                el(
                  'div',
                  { class: 'stepper' },
                  el('button', {
                    class: 'step',
                    text: '−',
                    title: t.less,
                    'aria-label': t.less,
                    on: { click: () => nudge(-1) },
                  }),
                  fields.quantity,
                  el('button', {
                    class: 'step',
                    text: '+',
                    title: t.more,
                    'aria-label': t.more,
                    on: { click: () => nudge(1) },
                  }),
                  fields.unit,
                ),
              );
              perType.appendChild(el('p', { class: 'hint', text: t.unitHint }));

              perType.appendChild(el('label', { text: t.store }));
              fields.store = el('select');
              fields.store.appendChild(el('option', { value: '', text: t.anywhere }));
              for (const zone of board.stores || []) {
                fields.store.appendChild(
                  el('option', { value: zone, text: this._storeName(zone) }),
                );
              }
              fields.store.value = item.store || '';
              perType.appendChild(fields.store);
              return;
            }

            if (isTask(type)) {
              perType.appendChild(el('label', { text: t.due }));
              fields.due = el('input', {
                type: 'date',
                value: (item.due || '').slice(0, 10),
              });
              perType.appendChild(fields.due);

              perType.appendChild(el('label', { text: t.duration }));
              fields.duration = el('input', {
                type: 'number',
                min: '0',
                step: 'any',
                value: item.duration ?? '',
              });
              fields.durationUnit = el('select');
              for (const unit of DURATION_UNITS) {
                fields.durationUnit.appendChild(
                  el('option', { value: unit, text: t.units[unit] }),
                );
              }
              fields.durationUnit.value = item.duration_unit || 'minutes';
              perType.appendChild(
                el('div', { class: 'duration' }, fields.duration, fields.durationUnit),
              );

              perType.appendChild(el('label', { text: t.tools }));
              fields.tools = el('input', { type: 'text', value: item.tools || '' });
              perType.appendChild(fields.tools);
              perType.appendChild(el('p', { class: 'hint', text: t.toolsHint }));
            }
            // With no type there is nothing here: just the name and the note.
          };

          fields.type.addEventListener?.('change', () => {
            type = fields.type.value;
            drawPerType();
          });
          drawPerType();

          content.appendChild(el('label', { text: t.note }));
          fields.note = el('textarea');
          fields.note.value = item.note || '';
          content.appendChild(fields.note);
        },
        buttons: [
          {
            label: t.delete,
            start: true,
            onClick: (close) => finish({ remove: true }, close),
          },
          { label: t.cancel, onClick: (close) => finish(null, close) },
          {
            label: t.save,
            primary: true,
            onClick: (close) =>
              finish(
                {
                  photoData,
                  photoTouched,
                  summary: fields.summary.value.trim(),
                  item_type: fields.type.value || null,
                  note: fields.note.value.trim() || null,
                  // Whatever the chosen kind does not show is cleared, so a
                  // product turned into a task keeps no stale shop.
                  quantity: fields.quantity
                    ? Number(fields.quantity.value) || null
                    : null,
                  unit: fields.unit ? fields.unit.value.trim() || null : null,
                  store: fields.store ? fields.store.value || null : null,
                  due: fields.due ? fields.due.value || null : null,
                  duration: fields.duration
                    ? Number(fields.duration.value) || null
                    : null,
                  duration_unit:
                    fields.duration && Number(fields.duration.value)
                      ? fields.durationUnit.value
                      : null,
                  tools: fields.tools ? fields.tools.value.trim() || null : null,
                },
                close,
              ),
          },
        ],
      });
    });

    if (!saved) return;
    if (saved.remove) {
      await this._remove(item);
      return;
    }
    if (!saved.summary) return;

    // The photo travels on its own, so it never reaches the item update.
    const { photoData, photoTouched, ...changes } = saved;

    try {
      await this._call('homebasket_lists/item/update', {
        entry_id: board.entry_id,
        uid: item.uid,
        ...changes,
      });

      if (photoTouched) {
        const key = `item:${item.uid}`;
        if (photoData) {
          await this._call('homebasket_lists/item/photo/set', {
            entry_id: board.entry_id,
            uid: item.uid,
            photo: photoData,
          });
          this._photos.set(key, photoData);
        } else {
          await this._call('homebasket_lists/item/photo/delete', {
            entry_id: board.entry_id,
            uid: item.uid,
          });
          this._photos.delete(key);
        }
      }
    } catch (err) {
      toast(this.shadowRoot, err.message || t.noAnswer, true);
    }
    await this._refresh();
  }

  /* ---------------- Product details ---------------- */

  /**
   * Everything HomeBasket holds on a product.
   *
   * It reads HomeBasket's cache through the integration, so opening this costs
   * no network request.
   */
  async _openProductDetails(product) {
    const t = this._t;
    let body;

    openDialog(this.shadowRoot, {
      title: t.details,
      wide: true,
      build: (content) => {
        body = el('div', { class: 'details' });
        body.appendChild(el('div', { class: 'empty', text: t.loading }));
        content.appendChild(body);

        this._call('homebasket_lists/product/details', { code: product.code })
          .then(({ details }) => {
            body.replaceChildren(
              details
                ? this._renderDetails(details, product, t)
                : el('div', { class: 'empty' }, el('p', { text: t.noDetails })),
            );
          })
          .catch((err) => {
            body.replaceChildren(
              el('div', { class: 'empty' }, el('p', { text: err.message || t.noAnswer })),
            );
          });
      },
      buttons: [{ label: t.close, primary: true, onClick: (close) => close() }],
    });
  }

  _renderDetails(details, product, t) {
    const fragment = document.createDocumentFragment();

    const shot = el('div', { class: 'shot' });
    const picture = details.images?.front || details.image || product.image;
    shot.appendChild(
      picture ? el('img', { src: picture, alt: '', loading: 'lazy' }) : icon('image'),
    );
    fragment.appendChild(
      el(
        'div',
        { class: 'details-head' },
        shot,
        el(
          'div',
          { class: 'who' },
          el('div', { class: 'name', text: product.name || details.label }),
          details.generic_name && details.generic_name !== details.name
            ? el('div', { class: 'sub', text: details.generic_name })
            : null,
          el('div', { class: 'sub', text: (product.codes || [details.code]).join(', ') }),
        ),
      ),
    );

    const grades = el('div', { class: 'grades' });
    const { nutriscore, nova, ecoscore } = details.grades || {};
    if (nutriscore) grades.appendChild(gradeBadge(nutriscore, nutriscore, t.nutriScore));
    if (nova) {
      grades.appendChild(gradeBadge(`n${nova}`, String(nova), t.novaGroup, t.novaExplained[nova]));
    }
    if (ecoscore) grades.appendChild(gradeBadge(ecoscore, ecoscore, t.ecoScore));
    if (grades.children.length) fragment.appendChild(grades);

    if (details.nutriments?.length) {
      const table = el('table', { class: 'facts' });
      const SUB_ROWS = ['saturated-fat', 'sugars'];
      for (const row of details.nutriments) {
        table.appendChild(
          el(
            'tr',
            {},
            el('td', {
              class: SUB_ROWS.includes(row.key) ? 'indent' : '',
              text: t.nutriments[row.key] || row.label,
            }),
            el('td', { text: `${row.value} ${row.unit}` }),
          ),
        );
      }
      fragment.append(el('h4', { text: t.sectionNutrition }), table);
    }

    if (details.ingredients) {
      fragment.append(
        el('h4', { text: t.sectionIngredients }),
        el('p', { text: details.ingredients }),
      );
    }

    const rows = [
      [t.fieldBrand, details.brands?.join(', ') || details.brand],
      [t.fieldQuantity, details.quantity],
      [t.fieldCategories, details.categories?.join(' · ')],
      [t.fieldLabels, details.labels?.join(', ')],
      [t.fieldAllergens, details.allergens?.join(', ')],
      [t.fieldPackaging, details.packaging],
      [t.fieldOrigins, details.origins],
      [t.fieldStores, details.stores?.join(', ')],
      [t.fieldCountries, details.countries?.join(', ')],
    ].filter(([, value]) => value);

    if (rows.length) {
      const list = el('dl', { class: 'about' });
      for (const [label, value] of rows) {
        list.append(el('dt', { text: label }), el('dd', { text: value }));
      }
      fragment.append(el('h4', { text: t.sectionAbout }), list);
    }

    if (details.url) {
      fragment.appendChild(
        el(
          'div',
          { class: 'source' },
          el('a', {
            href: details.url,
            target: '_blank',
            rel: 'noopener noreferrer',
            text: t.openOnOff,
          }),
        ),
      );
    }

    return fragment;
  }

  /* ---------------- Rendering ---------------- */

  _build() {
    const style = document.createElement('style');
    style.textContent = STYLES;

    this._title = el('h2');
    this._count = el('span', { class: 'pill' });
    this._syncButton = iconButton('sync', this._t.sync, () => this._sync());
    this._tabs = el('div', { class: 'tabs' });
    this._body = el('div', { class: 'body' });

    this._input = el('input', { type: 'text', autocomplete: 'off' });
    this._input.addEventListener('keydown', (event) => {
      if (this._onSuggestKey(event)) return;
      if (event.key === 'Enter') this._addItem(event.target.value);
    });
    this._input.addEventListener('input', (event) => this._onTyping(event.target.value));
    this._suggestBox = el('div', { class: 'suggest' });
    this._addButton = el(
      'button',
      {
        class: 'btn primary',
        title: this._t.add,
        'aria-label': this._t.add,
        on: { click: () => this._addItem(this._input.value) },
      },
      icon('plus'),
    );
    this._addRow = el('div', { class: 'add-row' }, this._input, this._addButton);

    this._card = el(
      'div',
      { class: 'card' },
      el(
        'header',
        {},
        this._title,
        el('div', { class: 'right' }, this._count, this._syncButton),
      ),
      this._tabs,
      this._body,
    );

    this.shadowRoot.append(style, this._card);
    this._rendered = true;
    this._render();
  }

  _render() {
    if (!this._rendered) return;
    const t = this._t;
    const board = this._board;

    this._title.textContent = this._config.title || board?.name || t.title;
    this._input.placeholder = t.addPlaceholder;
    this._syncButton.title = t.sync;
    this._body.replaceChildren();
    this._tabs.replaceChildren();

    if (this._error) {
      this._count.hidden = true;
      this._syncButton.hidden = true;
      this._body.appendChild(
        el(
          'div',
          { class: 'empty' },
          el('p', { text: this._error }),
          el('button', { class: 'btn', text: t.tryAgain, on: { click: () => this._refresh() } }),
        ),
      );
      return;
    }

    if (!board) {
      this._count.hidden = true;
      this._syncButton.hidden = true;
      this._body.appendChild(el('div', { class: 'empty' }, el('p', { text: t.noLists })));
      return;
    }

    // Tabs, only when there is a choice to make.
    if (this._lists.length > 1 && !this._config.list) {
      for (const entry of this._lists) {
        this._tabs.appendChild(
          el('button', {
            class: 'tab',
            role: 'tab',
            'aria-selected': String(entry.entry_id === board.entry_id),
            text: entry.name,
            on: {
              click: () => {
                this._selected = entry.entry_id;
                this._render();
              },
            },
          }),
        );
      }
    }

    const open = board.items.filter((item) => item.status !== STATUS_DONE);
    const done = board.items.filter((item) => item.status === STATUS_DONE);

    this._count.hidden = false;
    this._count.textContent = t.itemsLeft(open.length);
    this._syncButton.hidden = !board.linked_lists?.length;

    this._body.append(this._addRow, this._suggestBox);

    if (!board.items.length) {
      this._body.appendChild(el('div', { class: 'empty' }, el('p', { text: t.empty })));
      return;
    }

    if (this._config.group_by_store && board.stores?.length) {
      const groups = new Map();
      for (const item of open) {
        const key = isProduct(item.type) ? item.store || '' : '';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(item);
      }
      // Shops first, then the items that can be bought anywhere.
      const keys = [...groups.keys()].sort((a, b) => (a === '' ? 1 : b === '' ? -1 : 0));
      for (const key of keys) {
        if (keys.length > 1) {
          this._body.appendChild(
            el('div', { class: 'group-title' }, el('span', { text: this._storeName(key) || t.anywhere })),
          );
        }
        // The shop is already the heading, so repeating it on every row is noise.
        this._body.appendChild(
          this._renderItems(groups.get(key), t, { hideStore: keys.length > 1 }),
        );
      }
    } else if (open.length) {
      this._body.appendChild(this._renderItems(open, t));
    }

    if (done.length && this._config.show_completed) {
      this._body.appendChild(
        el('div', { class: 'group-title' }, el('span', { text: t.doneCount(done.length) })),
      );
      this._body.appendChild(this._renderItems(done, t));
    }
  }

  _renderItems(items, t, options = {}) {
    const list = el('div', { class: 'items' });
    for (const item of items) list.appendChild(this._renderItem(item, t, options));
    return list;
  }

  /** How many, as text with its own steppers, rather than a badge. */
  _renderAmount(item, t) {
    // The amount sits inside the row's own clickable area, so a tap on a step
    // must stop there instead of also opening the item sheet.
    const nudge = (event, by) => {
      event.stopPropagation();
      this._setQuantity(item, Math.max(1, (Number(item.quantity) || 0) + by));
    };

    return el(
      'span',
      { class: 'amount' },
      el('button', {
        class: 'step',
        text: '−',
        title: t.less,
        'aria-label': t.less,
        on: { click: (event) => nudge(event, -1) },
      }),
      el('span', { class: 'value', text: String(item.quantity) }),
      item.unit ? el('span', { class: 'unit', text: item.unit }) : null,
      el('button', {
        class: 'step',
        text: '+',
        title: t.more,
        'aria-label': t.more,
        on: { click: (event) => nudge(event, 1) },
      }),
    );
  }

  async _setQuantity(item, quantity) {
    try {
      await this._call('homebasket_lists/item/update', {
        entry_id: this._board.entry_id,
        uid: item.uid,
        quantity,
      });
    } catch (err) {
      toast(this.shadowRoot, err.message || this._t.noAnswer, true);
    }
    await this._refresh();
  }

  _renderItem(item, t, { hideStore = false } = {}) {
    const isDone = item.status === STATUS_DONE;

    const tick = el(
      'button',
      {
        class: 'tick',
        role: 'button',
        'aria-pressed': String(isDone),
        'aria-label': item.summary,
        on: { click: () => this._toggle(item) },
      },
      icon('check'),
    );

    const thumb = el('div', { class: 'thumb' });
    const image = el('img', { alt: '', loading: 'lazy', hidden: true });
    thumb.append(image, icon(isTask(item.type) ? 'task' : 'image'));
    if (item.has_photo) this._fillItemPhoto(item, image);
    else if (item.product?.has_photo) this._fillPhoto(item.product.code, image);
    else if (item.product?.image) {
      image.src = item.product.image;
      image.hidden = false;
      image.addEventListener('error', () => {
        image.hidden = true;
      });
    }

    const meta = el('div', { class: 'meta' });
    if (item.quantity) meta.appendChild(this._renderAmount(item, t));
    if (item.store && !hideStore && !isTask(item.type)) {
      meta.appendChild(el('span', { class: 'chip store', text: this._storeName(item.store) }));
    }
    if (isTask(item.type)) {
      if (item.due) {
        meta.appendChild(
          el('span', { class: 'chip qty', text: `${t.due}: ${item.due.slice(0, 10)}` }),
        );
      }
      const takes = this._durationLabel(item);
      if (takes) meta.appendChild(el('span', { class: 'chip qty', text: takes }));
      if (item.tools) meta.appendChild(el('span', { class: 'chip', text: item.tools }));
    }
    if (item.type) meta.appendChild(el('span', { class: 'chip', text: this._typeName(item.type) }));
    if (item.product?.category) {
      meta.appendChild(el('span', { class: 'chip', text: item.product.category }));
    }

    return el(
      'div',
      { class: isDone ? 'item done' : 'item' },
      tick,
      thumb,
      el(
        'div',
        {
          class: 'who',
          role: 'button',
          tabindex: '0',
          on: {
            click: () => this._openItem(item),
            keydown: (event) => {
              if (event.key === 'Enter' || event.key === ' ') this._openItem(item);
            },
          },
        },
        el('div', { class: 'name', text: item.summary }),
        meta.children.length ? meta : null,
      ),
      iconButton('trash', t.delete, () => this._remove(item), 'danger'),
    );
  }
}

/* ------------------------------------------------------------------ *
 * Visual editor
 * ------------------------------------------------------------------ */

const EDITOR_FIELDS = [
  { key: 'title', label: 'Title', type: 'text', hint: 'Leave empty to use the list name.' },
  {
    key: 'list',
    label: 'List',
    type: 'select',
    hint: 'Which list to show. All of them means a tab each.',
    // Filled in from the lists that actually exist.
    options: (editor) => [
      { value: '', label: 'All lists' },
      ...editor.lists.map((board) => ({ value: board.entry_id, label: board.name })),
    ],
  },
  {
    key: 'language',
    label: 'Language',
    type: 'select',
    options: () => [
      { value: '', label: "Home Assistant's language" },
      { value: 'bg', label: 'Български' },
      { value: 'en', label: 'English' },
    ],
  },
  { key: 'group_by_store', label: 'Group by shop', type: 'boolean' },
  { key: 'show_completed', label: 'Show completed items', type: 'boolean' },
];

class HomeBasketListsCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = { ...DEFAULT_CONFIG };
    this._lists = [];
  }

  get lists() {
    return this._lists;
  }

  setConfig(config) {
    this._config = { ...DEFAULT_CONFIG, ...config };
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._loadLists();
  }

  /** Read the lists once, so the picker offers the real ones. */
  async _loadLists() {
    try {
      const { lists } = await this._hass.connection.sendMessagePromise({
        type: 'homebasket_lists/lists',
      });
      this._lists = lists || [];
    } catch {
      this._lists = [];
    }
    this._render();
  }

  _update(key, value) {
    this._config = { ...this._config, [key]: value };
    this.dispatchEvent(
      new CustomEvent('config-changed', {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
  }

  _render() {
    const style = document.createElement('style');
    style.textContent = STYLES;

    const content = el('div', { class: 'editor' });
    for (const field of EDITOR_FIELDS) {
      const value = this._config[field.key];

      if (field.type === 'boolean') {
        const input = el('input', { type: 'checkbox' });
        input.checked = Boolean(value);
        input.addEventListener('change', () => this._update(field.key, input.checked));
        content.appendChild(
          el('label', { class: 'toggle' }, input, el('span', { text: field.label })),
        );
        continue;
      }

      let input;
      if (field.type === 'select') {
        input = el('select');
        const options = field.options(this);
        for (const option of options) {
          input.appendChild(el('option', { value: option.value, text: option.label }));
        }
        // A value saved earlier that no longer matches anything - a list that
        // was removed, or a name from before this was a picker - is kept as an
        // option of its own rather than silently swapped for another list.
        if (value && !options.some((option) => option.value === value)) {
          input.appendChild(el('option', { value, text: value }));
        }
        input.value = value ?? '';
        input.addEventListener('change', () => this._update(field.key, input.value || null));
      } else {
        input = el('input', { type: 'text', value: value ?? '' });
        input.addEventListener('change', () =>
          this._update(field.key, input.value.trim() || null),
        );
      }

      content.appendChild(
        el(
          'label',
          { class: 'field' },
          el('span', { text: field.label }),
          input,
          field.hint ? el('small', { text: field.hint }) : null,
        ),
      );
    }

    // The version, somewhere reachable without a browser console - which a
    // phone does not have.
    content.appendChild(
      el('small', {
        class: 'hint',
        text: stringsFor(this._hass?.locale?.language).cardVersion(VERSION),
      }),
    );

    this.shadowRoot.replaceChildren(style, content);
  }
}

// Guarded, so a second copy of this file - a leftover Lovelace resource
// alongside the one the integration serves - cannot throw and take the card
// down with it.
if (!customElements.get('homebasket-lists-card')) {
  customElements.define('homebasket-lists-card', HomeBasketListsCard);
  customElements.define('homebasket-lists-card-editor', HomeBasketListsCardEditor);

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'homebasket-lists-card',
    name: 'HomeBasket Lists',
    preview: false,
    description: 'Shopping lists that stay in step with the built-in to-do lists.',
    documentationURL: 'https://github.com/ivan1mihaylov/HomeBasket-Lists',
  });
}

console.info(
  `%c HOMEBASKET-LISTS-CARD %c ${VERSION} `,
  'color:#fff;background:#03a9f4;font-weight:700',
  'color:#03a9f4;background:#fff',
);
