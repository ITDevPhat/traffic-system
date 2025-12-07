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
import SelectFormInput from '@/components/from/SelectFormInput';
import { createViolationType, ViolationTypeCreateInput } from '@/services/violationTypesApi';
import { toast } from 'react-toastify';

const schema = yup.object({
  violation_type_code: yup
    .string()
    .required('Mã loại vi phạm là bắt buộc')
    .matches(/^[A-Z0-9_]+$/, 'Mã chỉ được chứa chữ in hoa, số và dấu gạch dưới'),
  description: yup.string().required('Mô tả là bắt buộc'),
  fine_amount: yup
    .number()
    .typeError('Mức phạt phải là số')
    .required('Mức phạt là bắt buộc')
    .min(0, 'Mức phạt phải lớn hơn hoặc bằng 0'),
  severity: yup
    .string()
    .required('Mức độ là bắt buộc')
    .oneOf(['low', 'medium', 'high'], 'Mức độ không hợp lệ'),
});

const severityOptions = [
  { value: 'low', label: 'Thấp' },
  { value: 'medium', label: 'Trung bình' },
  { value: 'high', label: 'Cao' },
];

export default function CreateViolationTypePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { control, handleSubmit } = useForm<ViolationTypeCreateInput>({
    resolver: yupResolver(schema),
    defaultValues: {
      violation_type_code: '',
      description: '',
      fine_amount: 0,
      severity: 'medium',
    },
  });

  const onSubmit = async (data: ViolationTypeCreateInput) => {
    setLoading(true);
    setError(null);
    try {
      await createViolationType(data);
      toast.success('Tạo loại vi phạm thành công!');
      router.push('/violations/types');
    } catch (err: any) {
      const errorMsg = err.message || 'Không thể tạo loại vi phạm';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageTitle title="Thêm loại vi phạm" subName="Tạo mới" />

      <Row>
        <Col lg={8} className="mx-auto">
          <Card className="shadow-sm">
            <Card.Header className="bg-white py-3">
              <h5 className="mb-0">📝 Thông tin loại vi phạm</h5>
            </Card.Header>

            <Card.Body>
              {error && (
                <Alert variant="danger" dismissible onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <form onSubmit={handleSubmit(onSubmit)}>
                <TextFormInput
                  name="violation_type_code"
                  control={control}
                  label="Mã loại vi phạm"
                  placeholder="VD: RED_LIGHT"
                  containerClassName="mb-3"
                  id="violation_type_code"
                  noValidate={false}
                  labelClassName=""
                />

                <TextAreaFormInput
                  name="description"
                  control={control}
                  label="Mô tả"
                  placeholder="Nhập mô tả chi tiết về loại vi phạm"
                  rows={4}
                  containerClassName="mb-3"
                  id="description"
                  noValidate={false}
                />

                <TextFormInput
                  name="fine_amount"
                  control={control}
                  label="Mức phạt (VNĐ)"
                  type="number"
                  placeholder="500000"
                  containerClassName="mb-3"
                  id="fine_amount"
                  noValidate={false}
                  labelClassName=""
                />

                <SelectFormInput
                  name="severity"
                  control={control}
                  label="Mức độ"
                  options={severityOptions}
                  containerClassName="mb-3"
                  id="severity"
                  className=""
                  labelClassName=""
                  noValidate={false}
                />

                <div className="d-flex gap-2 justify-content-end mt-4">
                  <Button
                    variant="secondary"
                    onClick={() => router.push('/violations/types')}
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
                        Tạo loại vi phạm
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
