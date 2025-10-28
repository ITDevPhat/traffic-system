'use client';

import { useSession } from 'next-auth/react';
import { usePathname, useRouter } from 'next/navigation';
import { Suspense } from 'react';
import FallbackLoading from '../FallbackLoading';
const AuthProtectionWrapper = ({
  children
}) => {
  const {
    status
  } = useSession();
  const {
    push
  } = useRouter();
  const pathname = usePathname();
  if (status == 'unauthenticated') {
    push(`/auth/sign-in?redirectTo=${pathname}`);
    return <FallbackLoading />;
  }
  return <Suspense>{children}</Suspense>;
};
export default AuthProtectionWrapper;