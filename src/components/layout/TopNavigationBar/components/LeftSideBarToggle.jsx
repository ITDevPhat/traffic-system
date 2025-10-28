'use client';

import IconifyIcon from '@/components/wrappers/IconifyIcon';
import React, { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { useLayoutContext } from '@/context/useLayoutContext';

const LeftSideBarToggle = () => {
  const context = useLayoutContext();
  const pathname = usePathname();
  const isFirstRender = useRef(true);

  const handleMenuSize = () => {
    // Always use current context value, not stale closure
    const currentSize = context.menu?.size || 'default';
    const newSize = currentSize === 'default' ? 'condensed' : 'default';
    
    console.log(`🔄 Topbar toggle: ${currentSize} → ${newSize}`);
    
    // ONLY update menu size, don't touch backdrop!
    context.updateSettings({
      theme: context.theme,
      topbarTheme: context.topbarTheme,
      menu: {
        ...context.menu,
        size: newSize
      }
    });
  };

  // Remove automatic backdrop toggle on pathname change
  // This was causing sidebar to be blocked
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
    }
    // Removed automatic toggleBackdrop - only manual mobile toggle should use it
  }, [pathname]);

  return <div className="topbar-item">
      <button type="button" onClick={handleMenuSize} className="button-toggle-menu topbar-button">
        <IconifyIcon icon="ri:menu-2-line" width={24} height={24} className="fs-24" />
      </button>
    </div>;
};

export default LeftSideBarToggle;