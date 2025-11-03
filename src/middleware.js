import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
  function middleware(request) {
    const token = request.nextauth.token;
    const { pathname } = request.nextUrl;
    
    // Root redirect
    if (pathname === '/') {
      return NextResponse.redirect(new URL('/dashboards/analytics', request.url));
    }
    
    // Auth pages - redirect to dashboard if already logged in
    if (pathname.startsWith('/auth/sign-in') || pathname.startsWith('/auth/sign-up')) {
      if (token) {
        return NextResponse.redirect(new URL('/dashboards/analytics', request.url));
      }
    }
    
    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const { pathname } = req.nextUrl;
        
        // Public paths - không cần auth
        if (
          pathname.startsWith('/auth') ||
          pathname.startsWith('/api/auth') ||
          pathname.startsWith('/_next') ||
          pathname.startsWith('/favicon')
        ) {
          return true;
        }
        
        // Protected paths - cần auth
        return !!token;
      },
    },
    pages: {
      signIn: '/auth/sign-in',
    },
  }
);

export const config = {
  matcher: [
    '/',
    '/dashboards/:path*',
    '/detection/:path*',
    '/auth/:path*',
    // Add other protected routes here
  ],
};