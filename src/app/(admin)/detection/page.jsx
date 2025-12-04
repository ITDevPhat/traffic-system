'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DetectionPage() {
  const router = useRouter();
  
  useEffect(() => {
    // Redirect to /detection/cameras
    router.replace('/detection/cameras');
  }, [router]);
  
  return null;
}
