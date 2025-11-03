'use client';

import avatar1 from '@/assets/images/users/avatar-1.jpg';
import IconifyIcon from '@/components/wrappers/IconifyIcon';
import Image from 'next/image';
import Link from 'next/link';
import { Dropdown, DropdownHeader, DropdownItem, DropdownMenu, DropdownToggle } from 'react-bootstrap';
import { signOut, useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

const ProfileDropdown = () => {
  const { data: session } = useSession();
  const router = useRouter();
  
  const handleLogout = async () => {
    await signOut({ 
      redirect: false,
      callbackUrl: '/auth/sign-in' 
    });
    router.push('/auth/sign-in');
  };
  
  // Get user info from session
  const userName = session?.user?.name || session?.user?.username || 'Guest';
  const userRole = session?.user?.role || 'User';
  
  return <Dropdown className="topbar-item" drop="down">
      <DropdownToggle as={'a'} type="button" className="topbar-button content-none" id="page-header-user-dropdown " data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
        <span className="d-flex align-items-center">
          <Image className="rounded-circle" width={32} src={avatar1} alt="avatar-3" />
        </span>
      </DropdownToggle>
      <DropdownMenu className="dropdown-menu-end">
        <DropdownHeader as={'h6'} className="dropdown-header">
          Welcome {userName}!
        </DropdownHeader>
        <div className="dropdown-item-text">
          <small className="text-muted">Role: {userRole}</small>
        </div>
        <div className="dropdown-divider my-1" />
        <DropdownItem as={Link} href="/profile">
          <IconifyIcon icon="solar:user-id-broken" className="align-middle me-2 fs-18" />
          <span className="align-middle">My Profile</span>
        </DropdownItem>
        <DropdownItem as={Link} href="/pages/pricing">
          <IconifyIcon icon="solar:wallet-broken" className="align-middle me-2 fs-18" />
          <span className="align-middle">Pricing</span>
        </DropdownItem>
        <DropdownItem as={Link} href="/support/faqs">
          <IconifyIcon icon="solar:help-broken" className="align-middle me-2 fs-18" />
          <span className="align-middle">Help</span>
        </DropdownItem>
        <DropdownItem as={Link} href="/auth/lock-screen">
          <IconifyIcon icon="solar:lock-keyhole-broken" className="align-middle me-2 fs-18" />
          <span className="align-middle">Lock screen</span>
        </DropdownItem>
        <div className="dropdown-divider my-1" />
        <DropdownItem onClick={handleLogout} className="text-danger" style={{ cursor: 'pointer' }}>
          <IconifyIcon icon="solar:logout-3-broken" className="align-middle me-2 fs-18" />
          <span className="align-middle">Logout</span>
        </DropdownItem>
      </DropdownMenu>
    </Dropdown>;
};
export default ProfileDropdown;