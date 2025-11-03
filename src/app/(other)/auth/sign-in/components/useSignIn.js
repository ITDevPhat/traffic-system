'use client';

import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { useNotificationContext } from '@/context/useNotificationContext';
import useQueryParams from '@/hooks/useQueryParams';
const useSignIn = () => {
  const [loading, setLoading] = useState(false);
  const {
    push
  } = useRouter();
  const {
    showNotification
  } = useNotificationContext();
  const queryParams = useQueryParams();
  const loginFormSchema = yup.object({
    username: yup.string().required('Vui lòng nhập tên đăng nhập hoặc email'),
    password: yup.string().required('Vui lòng nhập mật khẩu')
  });
  const {
    control,
    handleSubmit
  } = useForm({
    resolver: yupResolver(loginFormSchema),
    defaultValues: {
      username: 'admin',
      password: 'Admin@123'
    }
  });
  const login = handleSubmit(async values => {
    setLoading(true);
    signIn('credentials', {
      redirect: false,
      email: values?.username,  // NextAuth expects 'email' field, but we send username
      password: values?.password
    }).then(res => {
      if (res?.ok) {
        push(queryParams['redirectTo'] ?? '/dashboards/analytics');
        showNotification({
          message: 'Đăng nhập thành công. Đang chuyển hướng....',
          variant: 'success'
        });
      } else {
        showNotification({
          message: res?.error ?? 'Tên đăng nhập hoặc mật khẩu không đúng',
          variant: 'danger'
        });
      }
    });
    setLoading(false);
  });
  return {
    loading,
    login,
    control
  };
};
export default useSignIn;