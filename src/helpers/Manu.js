import { MENU_ITEMS } from '@/assets/data/menu-items';
export const getMenuItems = () => {
  return MENU_ITEMS;
};
export const findAllParent = (menuItems, menuItem) => {
  let parents = [];
  const parent = findMenuItem(menuItems, menuItem.parentKey);
  if (parent) {
    parents.push(parent.key);
    if (parent.parentKey) {
      parents = [...parents, ...findAllParent(menuItems, parent)];
    }
  }
  return parents;
};
const normalizeUrl = (u) => (u || '').replace(/\/$/, '');
export const getMenuItemFromURL = (items, url) => {
  const needle = normalizeUrl(url);
  if (items instanceof Array) {
    for (const item of items) {
      const foundItem = getMenuItemFromURL(item, needle);
      if (foundItem) {
        return foundItem;
      }
    }
  } else {
    if (normalizeUrl(items.url) == needle) return items;
    if (items.children != null) {
      for (const item of items.children) {
        if (normalizeUrl(item.url) == needle) return item;
      }
    }
  }
};
export const findMenuItem = (menuItems, menuItemKey) => {
  if (menuItems && menuItemKey) {
    for (const item of menuItems) {
      if (item.key === menuItemKey) {
        return item;
      }
      const found = findMenuItem(item.children, menuItemKey);
      if (found) return found;
    }
  }
  return null;
};