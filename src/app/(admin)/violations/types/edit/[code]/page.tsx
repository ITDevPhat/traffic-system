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
import SelectFormInput from '@/components/from/SelectFormInput';
import {
  fetchViolationTypeByCode,
  updateViolationType,
  ViolationTypeUpdateInput,
} from '@/services/violationTypesApi';
import { toast } from 'react-toastify';

const schema = yup.object({
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

export default function EditViolationTypePage() {
  const router = useRouter();
  const params = useParams();
  const code = params.code as string;

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [violationTypeCode, setViolationTypeCode] = useState<string>('');

  const { control, handleSubmit, reset } = useForm<ViolationTypeUpdateInput>({
    resolver: yupResolver(schema),
    defaultValues: {
      description: '',
      fine_amount: 0,
      severity: 'medium',
    },
  });

  useEffect(() => {
    const loadData = async () => {
      setLoadingData(true);
      setError(null);
      try {
        const data = await fetchViolationTypeByCode(code);
        setViolationTypeCode(data.violation_type_code);
        reset({
          description: data.description,
          fine_amount: data.fine_amount,
          severity: data.severity,
        });
      } catch (err: any) {
        const errorMsg = err.message || 'Không thể tải thông tin loại vi phạm';
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoadingData(false);
      }
    };

    if (code) {
      loadData();
    }
  }, [code, reset]);

  const onSubmit = async (data: ViolationTypeUpdateInput) => {
    setLoading(true);
    setError(null);
    try {
      await updateViolationType(code, data);
      toast.success('Cập nhật loại vi phạm thành công!');
      router.push('/violations/types');
    } catch (err: any) {
      const errorMsg = err.message || 'Không thể cập nhật loại vi phạm';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageTitle title="Chỉnh sửa loại vi phạm" subName="Cập nhật" />

      <Row>
        <Col lg={8} className="mx-auto">
          <Card className="shadow-sm">
            <Card.Header className="bg-white py-3">
              <h5 className="mb-0">✏️ Chỉnh sửa thông tin loại vi phạm</h5>
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
                  <div className="mb-3">
                    <label className="form-label">Mã loại vi phạm</label>
                    <input
                      type="text"
                      className="form-control"
                      value={violationTypeCode}
                      disabled
                      readOnly
                    />
                    <small className="text-muted">Mã loại vi phạm không thể thay đổi</small>
                  </div>

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
