'use client';

import React, { useState } from 'react';
import { Card, Button, Row, Col, Alert } from 'react-bootstrap';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useRouter } from 'next/navigation';
import PageTitle from '@/components/PageTitle';
import TextFormInput from '@/components/from/TextFormInput';
import TextAreaFormInput from '@/components/from/TextAreaFormInput';
import { createLocation, LocationCreateInput } from '@/services/locationsApi';
import { toast } from 'react-toastify';

const schema = yup.object({
  name: yup.string().required('Tên vị trí là bắt buộc'),
  address: yup.string(),
  latitude: yup
    .number()
    .transform((value) => (isNaN(value) ? undefined : value))
    .nullable()
    .typeError('Vĩ độ phải là số'),
  longitude: yup
    .number()
    .transform((value) => (isNaN(value) ? undefined : value))
    .nullable()
    .typeError('Kinh độ phải là số'),
  description: yup.string(),
});

export default function CreateLocationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { control, handleSubmit } = useForm<LocationCreateInput>({
    resolver: yupResolver(schema),
    defaultValues: {
      name: '',
      address: '',
      latitude: undefined,
      longitude: undefined,
      description: '',
    },
  });

  const onSubmit = async (data: LocationCreateInput) => {
    setLoading(true);
    setError(null);
    try {
      await createLocation(data);
      toast.success('Tạo vị trí thành công!');
      router.push('/locations');
    } catch (err: any) {
      const errorMsg = err.message || 'Không thể tạo vị trí';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageTitle title="Thêm vị trí mới" subName="Tạo mới" />

      <Row>
        <Col lg={8} className="mx-auto">
          <Card className="shadow-sm">
            <Card.Header className="bg-white py-3">
              <h5 className="mb-0">📍 Thông tin vị trí</h5>
            </Card.Header>

            <Card.Body>
              {error && (
                <Alert variant="danger" dismissible onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <form onSubmit={handleSubmit(onSubmit)}>
                <TextFormInput
                  name="name"
                  control={control}
                  label="Tên vị trí"
                  placeholder="VD: Ngã tư Hàng Xanh"
                  containerClassName="mb-3"
                  id="name"
                  noValidate={false}
                  labelClassName=""
                />

                <TextFormInput
                  name="address"
                  control={control}
                  label="Địa chỉ"
                  placeholder="VD: Bình Thạnh, TP.HCM"
                  containerClassName="mb-3"
                  id="address"
                  noValidate={false}
                  labelClassName=""
                />

                <Row>
                  <Col md={6}>
                    <TextFormInput
                      name="latitude"
                      control={control}
                      label="Vĩ độ (Latitude)"
                      type="number"
                      step="0.000001"
                      placeholder="10.801046"
                      containerClassName="mb-3"
                      id="latitude"
                      noValidate={false}
                      labelClassName=""
                    />
                  </Col>
                  <Col md={6}>
                    <TextFormInput
                      name="longitude"
                      control={control}
                      label="Kinh độ (Longitude)"
                      type="number"
                      step="0.000001"
                      placeholder="106.711200"
                      containerClassName="mb-3"
                      id="longitude"
                      noValidate={false}
                      labelClassName=""
                    />
                  </Col>
                </Row>

                <TextAreaFormInput
                  name="description"
                  control={control}
                  label="Mô tả (tùy chọn)"
                  placeholder="Nhập mô tả chi tiết về vị trí"
                  rows={3}
                  containerClassName="mb-3"
                  id="description"
                  noValidate={false}
                />

                <div className="d-flex gap-2 justify-content-end mt-4">
                  <Button
                    variant="secondary"
                    onClick={() => router.push('/locations')}
                    disabled={loading}
                  >
                    Hủy
                  </Button>
                  <Button variant="primary" type="submit" disabled={loading}>
                    {loading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" />
                        Đang tạo...
                      </>
                    ) : (
                      <>
                        <i className="ri-save-line me-1"></i>
                        Tạo vị trí
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );
}
