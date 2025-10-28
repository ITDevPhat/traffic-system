'use client';

import IconifyIcon from '@/components/wrappers/IconifyIcon';
import { useLayoutContext } from '@/context/useLayoutContext';
import useViewPort from '@/hooks/useViewPort';
import { useEffect } from 'react';

const HoverMenuToggle = () => {
  const context = useLayoutContext();
  const {
    width
  } = useViewPort();
  
  // Fixed: Re-enable sidebar toggle functionality
  const handleHoverMenu = () => {
    // Always use current context value
    const currentSize = context.menu?.size || 'default';
    const newSize = currentSize === 'default' ? 'condensed' : 'default';
    console.log(`🔄 Sidebar toggle: ${currentSize} → ${newSize}`);
    
    // ONLY update menu size, preserve other settings
    if (context.updateSettings) {
      context.updateSettings({
        theme: context.theme,
        topbarTheme: context.topbarTheme,
        menu: {
          ...context.menu,
          size: newSize
        }
      });
    }
  };
  
  return <button 
    type="button" 
    onClick={handleHoverMenu} 
    className="button-sm-hover" 
    aria-label="Toggle Sidebar"
  >
    <IconifyIcon 
      height={24} 
      width={24} 
      icon="ri:menu-2-line" 
      className="button-sm-hover-icon" 
    />
  </button>;
};

export default HoverMenuToggle;