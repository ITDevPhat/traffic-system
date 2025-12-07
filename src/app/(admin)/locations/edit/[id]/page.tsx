'use client';

import React, { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Alert } from 'react-bootstrap';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useRouter, useParams } from 'next/navigation';
import PageTitle from '@/components/PageTitle';
import TextFormInput from '@/components/from/TextFormInput';
import TextAreaFormInput from '@/components/from/TextAreaFormInput';
import { fetchLocationById, updateLocation, LocationUpdateInput } from '@/services/locationsApi';
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

export default function EditLocationPage() {
  const router = useRouter();
  const params = useParams();
  const locationId = parseInt(params.id as string);

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { control, handleSubmit, reset } = useForm<LocationUpdateInput>({
    resolver: yupResolver(schema),
    defaultValues: {
      name: '',
      address: '',
      latitude: undefined,
      longitude: undefined,
      description: '',
    },
  });

  useEffect(() => {
    const loadData = async () => {
      setLoadingData(true);
      setError(null);
      try {
        const data = await fetchLocationById(locationId);
        reset({
          name: data.name,
          address: data.address || '',
          latitude: data.latitude,
          longitude: data.longitude,
          description: data.description || '',
        });
      } catch (err: any) {
        const errorMsg = err.message || 'Không thể tải thông tin vị trí';
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoadingData(false);
      }
    };

    if (locationId) {
      loadData();
    }
  }, [locationId, reset]);

  const onSubmit = async (data: LocationUpdateInput) => {
    setLoading(true);
    setError(null);
    try {
      await updateLocation(locationId, data);
      toast.success('Cập nhật vị trí thành công!');
      router.push('/locations');
    } catch (err: any) {
      const errorMsg = err.message || 'Không thể cập nhật vị trí';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageTitle title="Chỉnh sửa vị trí" subName="Cập nhật" />

      <Row>
        <Col lg={8} className="mx-auto">
          <Card className="shadow-sm">
            <Card.Header className="bg-white py-3">
              <h5 className="mb-0">📍 Chỉnh sửa thông tin vị trí</h5>
            </Card.Header>

            <Card.Body>
              {error && (
                <Alert variant="danger" dismissible onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              {loadingData ? (
                <div className="text-center py-5">
                  <div className="spinner-border text-primary" role="status"></div>
                  <p className="mt-2 text-muted">Đang tải dữ liệu...</p>
                </div>
              ) : (
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
                          Đang cập nhật...
                        </>
                      ) : (
                        <>
                          <i className="ri-save-line me-1"></i>
                          Cập nhật
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );
}
