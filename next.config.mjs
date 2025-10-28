/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  // Silence specific Sass deprecations per official docs (Dart Sass)
  sassOptions: {
    silenceDeprecations: ['mixed-decls']
  },
  async rewrites() {
    return [
      {
        source: '/_next/static/chunks/react-toastify.esm.mjs.map',
        destination: '/_noop.map'
      },
      {
        // Chrome DevTools extension looks for this in some setups; serve noop to avoid 404 noise
        source: '/.well-known/appspecific/com.chrome.devtools.json',
        destination: '/_noop.map'
      }
    ]
  },
  
  // Tối ưu cho dev mode
  eslint: {
    ignoreDuringBuilds: true, // Bỏ qua ESLint trong dev để tăng tốc
  },
  
  experimental: {
    optimizeCss: true,
    // Tắt Turbopack để tránh cảnh báo do có webpack config tùy biến
    // (Nếu muốn dùng Turbopack, hãy xoá hàm webpack phía dưới.)
    optimizePackageImports: [
      '@iconify/react', 
      'react-bootstrap', 
      'apexcharts',
      'react-apexcharts',
      '@fullcalendar/react',
      '@fullcalendar/daygrid',
      '@fullcalendar/timegrid',
      '@fullcalendar/interaction',
      '@fullcalendar/list',
      '@fullcalendar/bootstrap'
    ],
    // Tối ưu bundle splitting
    webpackBuildWorker: true,
  },
  
  // Lưu ý: Bật Turbopack và webpack cùng lúc gây cảnh báo.
  // Nếu muốn dùng Turbopack, hãy xoá đoạn webpack dưới đây.
  webpack: (config, { dev, isServer }) => {
    if (dev) {
      // Tối ưu watch options cho dev mode
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 200, // Giảm từ 300ms xuống 200ms
        ignored: ['**/node_modules/**', '**/.next/**'], // Bỏ qua các thư mục không cần watch
      }
      
      // Tối ưu resolve cho dev mode
      config.resolve.symlinks = false
      config.resolve.cacheWithContext = false
      
      // Tối ưu module resolution
      config.resolve.modules = ['node_modules']
    }
    
    // Tối ưu cho cả dev và production
    config.optimization = {
      ...config.optimization,
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          // Tách ApexCharts thành chunk riêng
          apexcharts: {
            test: /[\\/]node_modules[\\/](apexcharts|react-apexcharts)[\\/]/,
            name: 'apexcharts',
            chunks: 'all',
            priority: 20,
          },
          // Tách FullCalendar thành chunk riêng
          fullcalendar: {
            test: /[\\/]node_modules[\\/]@fullcalendar[\\/]/,
            name: 'fullcalendar',
            chunks: 'all',
            priority: 20,
          },
          // Tách Bootstrap thành chunk riêng
          bootstrap: {
            test: /[\\/]node_modules[\\/](bootstrap|react-bootstrap)[\\/]/,
            name: 'bootstrap',
            chunks: 'all',
            priority: 20,
          },
        },
      },
    }
    
    return config
  }
};

export default nextConfig;
