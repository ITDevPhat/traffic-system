/**
 * Next.js API Route: /api/videos
 * Proxy to FastAPI backend /api/videos endpoint
 */

import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    // Get query params from request
    const searchParams = request.nextUrl.searchParams;
    const skip = searchParams.get('skip') || '0';
    const limit = searchParams.get('limit') || '100';
    const status = searchParams.get('status') || '';
    
    // Build backend URL
    const params = new URLSearchParams();
    params.append('skip', skip);
    params.append('limit', limit);
    if (status) {
      params.append('status', status);
    }
    
    const backendUrl = `${API_URL}/api/videos?${params.toString()}`;
    
    // Fetch from FastAPI backend
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Add cache control for realtime data
      cache: 'no-store',
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      return NextResponse.json(
        { error: error.detail || 'Failed to fetch videos' },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    
    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
      },
    });
  } catch (error: any) {
    console.error('❌ API /api/videos error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

