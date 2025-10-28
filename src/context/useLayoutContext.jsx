'use client';

import { createContext, use, useCallback, useEffect, useMemo, useState } from 'react';
import { toggleDocumentAttribute } from '@/utils/layout';
import useQueryParams from '@/hooks/useQueryParams';
import useLocalStorage from '@/hooks/useLocalStorage';
const ThemeContext = createContext(undefined);
const useLayoutContext = () => {
  const context = use(ThemeContext);
  if (!context) {
    throw new Error('useLayoutContext can only be used within LayoutProvider');
  }
  return context;
};
const getPreferredTheme = () => window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
const LayoutProvider = ({
  children
}) => {
  const queryParams = useQueryParams();
  const override = !!(queryParams.layout_theme || queryParams.topbar_theme || queryParams.menu_theme || queryParams.menu_size);
  const INIT_STATE = {
    theme: 'dark',
    topbarTheme: 'dark',
    menu: {
      theme: 'dark',
      size: 'condensed'
    }
  };
  const [settings, setSettings] = useLocalStorage('__REBACK_NEXT_CONFIG__', INIT_STATE, override);
  const [offcanvasStates, setOffcanvasStates] = useState({
    showActivityStream: false,
    showBackdrop: false
  });

  // update settings (wrapped with useCallback to prevent re-renders)
  const updateSettings = useCallback(_newSettings => {
    setSettings(prev => ({
      ...prev,
      ..._newSettings
    }));
  }, [setSettings]);

  // toggle activity stream offcanvas
  const toggleActivityStream = () => {
    setOffcanvasStates({
      ...offcanvasStates,
      showActivityStream: !offcanvasStates.showActivityStream
    });
  };
  const activityStream = useMemo(() => ({
    open: offcanvasStates.showActivityStream,
    toggle: toggleActivityStream
  }), [offcanvasStates.showActivityStream, toggleActivityStream]);

  // toggle backdrop
  const toggleBackdrop = useCallback(() => {
    const htmlTag = document.getElementsByTagName('html')[0];
    setOffcanvasStates(prev => {
      if (prev.showBackdrop) {
        htmlTag.classList.remove('sidebar-enable');
      } else {
        htmlTag.classList.add('sidebar-enable');
      }
      return {
        ...prev,
        showBackdrop: !prev.showBackdrop
      };
    });
  }, []);
  useEffect(() => {
    toggleDocumentAttribute('data-bs-theme', settings.theme);
    toggleDocumentAttribute('data-topbar-color', settings.topbarTheme);
    toggleDocumentAttribute('data-menu-color', settings.menu.theme);
    toggleDocumentAttribute('data-menu-size', settings.menu.size);
    return () => {
      toggleDocumentAttribute('data-bs-theme', settings.theme, true);
      toggleDocumentAttribute('data-topbar-color', settings.topbarTheme, true);
      toggleDocumentAttribute('data-menu-color', settings.menu.theme, true);
      toggleDocumentAttribute('data-menu-size', settings.menu.size, true);
    };
  }, [settings]);
  return <ThemeContext.Provider value={useMemo(() => ({
    ...settings,
    themeMode: settings.theme,
    activityStream,
    toggleBackdrop,
    updateSettings  // ← Add this so child components can update settings
  }), [settings, activityStream, toggleBackdrop, updateSettings])}>
      {children}
      {offcanvasStates.showBackdrop && <div className="offcanvas-backdrop fade show" onClick={toggleBackdrop} />}
    </ThemeContext.Provider>;
};
export { LayoutProvider, useLayoutContext };