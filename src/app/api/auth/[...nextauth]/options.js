import CredentialsProvider from 'next-auth/providers/credentials';
import { loginUser } from '@/services/api';

/**
 * NextAuth configuration tích hợp với FastAPI backend
 * 
 * Backend API: http://localhost:8000/api/auth
 * 
 * Default credentials:
 * - Username: admin
 * - Password: Admin@123
 * 
 * Để tạo admin user, chạy:
 * cd traffic-server && python -m app.scripts.seed_admin
 */

export const options = {
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: {
          label: 'Email or Username:',
          type: 'text',
          placeholder: 'Enter your username or email'
        },
        password: {
          label: 'Password',
          type: 'password',
          placeholder: 'Enter your password'
        }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error('Missing username or password');
        }
        
        try {
          // Call FastAPI backend login endpoint
          const response = await loginUser(credentials.email, credentials.password);
          
          if (response && response.access_token && response.user) {
            // Return user object với access_token
            return {
              id: response.user.user_id.toString(),
              email: response.user.email || response.user.username,
              name: response.user.full_name || response.user.username,
              username: response.user.username,
              role: response.user.role,
              accessToken: response.access_token,
              // Include additional user data
              avatar_url: response.user.avatar_url,
              last_login: response.user.last_login,
            };
          }
          
          return null;
        } catch (error) {
          console.error('Login error:', error);
          // Throw error để NextAuth hiển thị message
          throw new Error(error.message || 'Invalid credentials');
        }
      }
    })
  ],
  
  secret: process.env.NEXTAUTH_SECRET || 'kvwLrfri/MBznUCofIoRH9+NvGu6GqvVdqO3mor1GuA=',
  
  pages: {
    signIn: '/auth/sign-in',
    // signUp: '/auth/sign-up', // Uncomment if needed
    error: '/auth/sign-in', // Redirect errors to sign-in page
  },
  
  callbacks: {
    async signIn({ user, account, profile, email, credentials }) {
      // Allow sign in if user object exists
      return !!user;
    },
    
    async session({ session, token }) {
      // Add custom fields to session
      if (token) {
        session.user.id = token.id;
        session.user.username = token.username;
        session.user.role = token.role;
        session.user.accessToken = token.accessToken;
        session.user.avatar_url = token.avatar_url;
        session.user.last_login = token.last_login;
      }
      return session;
    },
    
    async jwt({ token, user, account }) {
      // Persist user data to token on initial sign in
      if (user) {
        token.id = user.id;
        token.username = user.username;
        token.role = user.role;
        token.accessToken = user.accessToken;
        token.avatar_url = user.avatar_url;
        token.last_login = user.last_login;
      }
      return token;
    }
  },
  
  session: {
    strategy: 'jwt',
    maxAge: 7 * 24 * 60 * 60, // 7 days (match backend ACCESS_TOKEN_EXPIRE_DAYS)
  },
  
  debug: process.env.NODE_ENV === 'development',
};