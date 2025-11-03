'use client';

import logoDark from '@/assets/images/logo-dark.png';
import LogoLight from '@/assets/images/logo-light.png';
import TextFormInput from '@/components/from/TextFormInput';
import PasswordFormInput from '@/components/from/PasswordFormInput';
import IconifyIcon from '@/components/wrappers/IconifyIcon';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect } from 'react';
import { Button, Card, CardBody, Col, Container, Row } from 'react-bootstrap';
import useSignIn from './useSignIn';
const SignIn = () => {
  useEffect(() => {
    document.body.classList.add('authentication-bg');
    return () => {
      document.body.classList.remove('authentication-bg');
    };
  }, []);

  // const messageSchema = yup.object({
  //   email: yup.string().email().required('Please enter Email'),
  //   password: yup.string().required('Please enter password'),
  // })

  // const { handleSubmit, control } = useForm({
  //   resolver: yupResolver(messageSchema),
  // })

  const {
    loading,
    login,
    control
  } = useSignIn();
  return <div className="account-pages pt-2 pt-sm-5 pb-4 pb-sm-5">
      <Container>
        <Row className="justify-content-center">
          <Col xl={5}>
            <Card className="auth-card">
              <CardBody className="px-3 py-5">
                <div className="mx-auto mb-4 text-center auth-logo">
                  <Link href="/dashboards/analytics" className="logo-dark">
                    <Image src={logoDark} height={32} alt="logo dark" />
                  </Link>
                  <Link href="/dashboards/analytics" className="logo-light">
                    <Image src={LogoLight} height={28} alt="logo light" />
                  </Link>
                </div>
                <h2 className="fw-bold text-uppercase text-center fs-18">Đăng Nhập</h2>
                <p className="text-muted text-center mt-1 mb-4">Nhập tên đăng nhập hoặc email và mật khẩu để truy cập bảng điều khiển.</p>
                <div className="px-4">
                  <form className="authentication-form" onSubmit={login}>
                    <div className="mb-3">
                      <TextFormInput 
                        control={control} 
                        name="username" 
                        type="text"
                        placeholder="Nhập tên đăng nhập hoặc email" 
                        className="bg-light bg-opacity-50 border-light py-2" 
                        label="Tên đăng nhập hoặc Email" 
                      />
                    </div>
                    <div className="mb-3">
                      <Link href="/auth/reset-password" className="float-end text-muted text-unline-dashed ms-1">
                        Quên mật khẩu
                      </Link>
                      <PasswordFormInput 
                        control={control} 
                        name="password" 
                        placeholder="Nhập mật khẩu của bạn" 
                        className="bg-light bg-opacity-50 border-light py-2" 
                        label="Mật khẩu" 
                      />
                    </div>
                    <div className="mb-3">
                      <div className="form-check">
                        <input type="checkbox" className="form-check-input" id="checkbox-signin" />
                        <label className="form-check-label" htmlFor="checkbox-signin">
                          Ghi nhớ đăng nhập
                        </label>
                      </div>
                    </div>
                    <div className="mb-1 text-center d-grid">
                      <button disabled={loading} className="btn btn-danger py-2 fw-medium" type="submit">
                        Đăng Nhập
                      </button>
                    </div>
                  </form>
                  <p className="mt-3 fw-semibold no-span">HOẶC đăng nhập bằng</p>
                  <div className="text-center">
                    <Button variant="outline-light" className="shadow-none">
                      <IconifyIcon icon="bxl:google" className="fs-20" />
                    </Button>
                    &nbsp;
                    <Button variant="outline-light" className="shadow-none">
                      <IconifyIcon icon="ri:facebook-fill" height={32} width={20} className="" />
                    </Button>
                    &nbsp;
                    <Button variant="outline-light" className="shadow-none">
                      <IconifyIcon icon="bxl:github" className="fs-20" />
                    </Button>
                  </div>
                </div>
              </CardBody>
            </Card>
            <p className="mb-0 text-center text-white">
              Chưa có tài khoản?{' '}
              <Link href="/auth/sign-up" className="text-reset text-unline-dashed fw-bold ms-1">
                Đăng Ký
              </Link>
            </p>
          </Col>
        </Row>
      </Container>
    </div>;
};
export default SignIn;