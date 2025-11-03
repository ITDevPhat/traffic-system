'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useNotificationContext } from '@/context/useNotificationContext';
import { registerUser } from '@/services/api';

const useSignUp = () => {
  const [loading, setLoading] = useState(false);
  const { push } = useRouter();
  const { showNotification } = useNotificationContext();

  // Validation schema
  const signUpFormSchema = yup.object({
    name: yup.string().required('Please enter your full name'),
    email: yup
      .string()
      .email('Please enter a valid email')
      .required('Please enter your email'),
    password: yup
      .string()
      .min(8, 'Password must be at least 8 characters')
      .required('Please enter your password'),
  });

  const { control, handleSubmit } = useForm({
    resolver: yupResolver(signUpFormSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
    },
  });

  const register = handleSubmit(async (values) => {
    setLoading(true);
    
    try {
      // Convert email to username (or extract username from email)
      const username = values.email.split('@')[0];
      
      // Call register API
      const response = await registerUser({
        username: username,
        password: values.password,
        email: values.email,
        full_name: values.name,
      });

      if (response && response.user_id) {
        showNotification({
          message: 'Account created successfully! Redirecting to login...',
          variant: 'success',
        });

        // Redirect to sign-in page after 1.5 seconds
        setTimeout(() => {
          push('/auth/sign-in');
        }, 1500);
      }
    } catch (error) {
      console.error('Registration error:', error);
      showNotification({
        message: error.message || 'Registration failed. Please try again.',
        variant: 'danger',
      });
    } finally {
      setLoading(false);
    }
  });

  return {
    loading,
    register,
    control,
  };
};

export default useSignUp;

