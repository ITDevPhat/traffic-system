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
import { createModel, ModelCreateInput } from '@/services/modelsApi';
import { toast } from 'react-toastify';

const schema = yup.object({
  name: yup.string().required('Tên mô hình là bắt buộc'),
  model_type: yup
    .string()
    .required('Loại mô hình là bắt buộc')
    .oneOf(['vehicle', 'plate', 'ocr', 'traffic_light', 'violation'], 'Loại mô hình không hợp lệ'),
  file_path: yup.string().required('Đường dẫn file là bắt buộc'),
  version: yup.string().required('Phiên bản là bắt buộc'),
  framework: yup.string().required('Framework là bắt buộc'),
  confidence_threshold: yup
    .number()
    .typeError('Ngưỡng confidence phải là số')
    .required('Ngưỡng confidence là bắt buộc')
    .min(0, 'Ngưỡng phải từ 0 đến 1')
    .max(1, 'Ngưỡng phải từ 0 đến 1'),
  description: yup.string(),
});

const modelTypeOptions = [
  { value: 'vehicle', label: 'Phương tiện' },
  { value: 'plate', label: 'Biển số' },
  { value: 'ocr', label: 'OCR' },
  { value: 'traffic_light', label: 'Đèn giao thông' },
  { value: 'violation', label: 'Vi phạm' },
];

export default function CreateModelPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { control, handleSubmit } = useForm<ModelCreateInput>({
    resolver: yupResolver(schema),
    defaultValues: {
      name: '',
      model_type: 'vehicle',
      file_path: '',
      version: '1.0',
      framework: 'YOLO',
      confidence_threshold: 0.5,
      description: '',
    },
  });

  const onSubmit = async (data: ModelCreateInput) => {
    setLoading(true);
    setError(null);
    try {
      await createModel(data);
      toast.success('Tạo mô hình thành công!');
      router.push('/models');
    } catch (err: any) {
      const errorMsg = err.message || 'Không thể tạo mô hình';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageTitle title="Thêm mô hình AI" subName="Tạo mới" />

      <Row>
        <Col lg={8} className="mx-auto">
          <Card className="shadow-sm">
            <Card.Header className="bg-white py-3">
              <h5 className="mb-0">🧠 Thông tin mô hình AI</h5>
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
                  label="Tên mô hình"
                  placeholder="VD: yolo_vehicle_11s"
                  containerClassName="mb-3"
                  id="name"
                  noValidate={false}
                  labelClassName=""
                />

                <SelectFormInput
                  name="model_type"
                  control={control}
                  label="Loại mô hình"
                  options={modelTypeOptions}
                  containerClassName="mb-3"
                  id="model_type"
                  className=""
                  labelClassName=""
                  noValidate={false}
                />

                <TextFormInput
                  name="file_path"
                  control={control}
                  label="Đường dẫn file"
                  placeholder="models/vehicle/yolo_vehicle_11s.pt"
                  containerClassName="mb-3"
                  id="file_path"
                  noValidate={false}
                  labelClassName=""
                />

                <Row>
                  <Col md={6}>
                    <TextFormInput
                      name="version"
                      control={control}
                      label="Phiên bản"
                      placeholder="1.0"
                      containerClassName="mb-3"
                      id="version"
                      noValidate={false}
                      labelClassName=""
                    />
                  </Col>
                  <Col md={6}>
                    <TextFormInput
                      name="framework"
                      control={control}
                      label="Framework"
                      placeholder="YOLOv11s"
                      containerClassName="mb-3"
                      id="framework"
                      noValidate={false}
                      labelClassName=""
                    />
                  </Col>
                </Row>

                <TextFormInput
                  name="confidence_threshold"
                  control={control}
                  label="Ngưỡng confidence (0-1)"
                  type="number"
                  step="0.01"
                  placeholder="0.5"
                  containerClassName="mb-3"
                  id="confidence_threshold"
                  noValidate={false}
                  labelClassName=""
                />

                <TextAreaFormInput
                  name="description"
                  control={control}
                  label="Mô tả (tùy chọn)"
                  placeholder="Nhập mô tả chi tiết về mô hình"
                  rows={3}
                  containerClassName="mb-3"
                  id="description"
                  noValidate={false}
                />

                <div className="d-flex gap-2 justify-content-end mt-4">
                  <Button
                    variant="secondary"
                    onClick={() => router.push('/models')}
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
                        Tạo mô hình
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
