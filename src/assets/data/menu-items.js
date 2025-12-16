
export const MENU_ITEMS = [{
  key: 'menu',
  label: 'MENU',
  isTitle: true
}, {
  key: 'detection',
  label: 'Realtime Detection',
  icon: 'ri:road-map-line',
  children: [
    {
      key: 'detection-live',
      label: 'Quan sát Camera',
      url: '/detection/cameras',
      parentKey: 'detection'
    },
    {
      key: 'detection-grid',
      label: 'Trích thông tin biển số xe',
      url: '/detection/ocr',
      parentKey: 'detection'
    },
    {
      key: 'detection-traffic-light',
      label: 'Giao thông vi phạm',
      url: '/detection/traffic-light',
      parentKey: 'detection'
    },
    // {
    //   key: 'detection-traffic-live',
    //   label: 'Giám sát đèn giao thông',
    //   url: '/detection/traffic-live',
    //   parentKey: 'detection'
    // }
  ]
}, 
// {
//   key: 'dashboards',
//   label: 'Dashboards',
//   icon: 'ri:dashboard-line',
//   children: [{
//     key: 'analytics',
//     label: 'Analytics',
//     url: '/dashboards/analytics',
//     parentKey: 'dashboards'
//   }, {
//     key: 'agent',
//     label: 'Agent',
//     url: '/dashboards/agent',
//     parentKey: 'dashboards'
//   }, {
//     key: 'customer',
//     label: 'Customer',
//     url: '/dashboards/customer',
//     parentKey: 'dashboards'
//   }]
// },
{
  key: 'management-section',
  label: 'QUẢN LÝ HỆ THỐNG',
  isTitle: true
},
{
  key: 'type-violation-management',
  label: 'Quản lý loại vi phạm',
  icon: 'ri:error-warning-line',
  children: [{
    key: 'list-type-violation',
    label: 'Danh sách loại vi phạm',
    url: '/violations/types',
    parentKey: 'type-violation-management'
  }, {
    key: 'add-type-violation',
    label: 'Thêm loại vi phạm',
    url: '/violations/types/create',
    parentKey: 'type-violation-management'
  }]
},
{
  key: 'model-management',
  label: 'Quản lý mô hình',
  icon: 'ri:cpu-line',
  children: [{
    key: 'lis-model',
    label: 'Danh sách mô hình',
    url: '/models',
    parentKey: 'model-management'
  }, {
    key: 'add-model',
    label: 'Thêm mô hình',
    url: '/models/create',
    parentKey: 'model-management'
  }]
},
{
  key: 'location-management',
  label: 'Quản lý vị trí',
  icon: 'ri:map-pin-line',
  children: [{
    key: 'list-location',
    label: 'Danh sách vị trí',
    url: '/locations',
    parentKey: 'location-management'
  }, {
    key: 'add-location',
    label: 'Thêm vị trí',
    url: '/locations/create',
    parentKey: 'location-management'
  }]
},
{
  key: 'camera-management',
  label: 'Quản lý camera',
  icon: 'ri:camera-3-line',
  children: [{
    key: 'list-camera',
    label: 'Danh sách camera',
    url: '/cameras',
    parentKey: 'camera-management'
  }, {
    key: 'add-camera',
    label: 'Thêm camera',
    url: '/cameras/create',
    parentKey: 'camera-management'
  }]
},
{
  key: 'video-job-management',
  label: 'Quản lý video job',
  icon: 'ri:movie-2-line',
  children: [{
    key: 'list-video-job',
    label: 'Danh sách video job',
    url: '/video-jobs',
    parentKey: 'video-job-management'
  }, {
    key: 'add-video-job',
    label: 'Thêm video job',
    url: '/video-jobs/create',
    parentKey: 'video-job-management'
  }]
},
{
  key: 'violation-management',
  label: 'Quản lý vi phạm',
  icon: 'ri:alert-line',
  children: [{
    key: 'list-violations',
    label: 'Danh sách vi phạm',
    url: '/violations/management',
    parentKey: 'violation-management'
  }]
}
];