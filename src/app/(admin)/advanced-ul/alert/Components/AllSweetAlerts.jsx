'use client';

import ComponentContainerCard from '@/components/ComponentContainerCard';
import { Button } from 'react-bootstrap';
import Swal from 'sweetalert2';
import withReactContent from 'sweetalert2-react-content';

// Tạo instance SweetAlert2 với React support
const MySwal = withReactContent(Swal);

const AllSweetAlerts = () => {
  return <>
      <ComponentContainerCard id="basic" title="Basic" titleClass="mb-3">
        <Button variant="primary" type="button" onClick={() => MySwal.fire({
        title: 'Any fool can use a computer',
        customClass: {
          confirmButton: `btn btn-primary w-xs mt-2`
        }
      })}>
          Click me
        </Button>
      </ComponentContainerCard>

      <ComponentContainerCard id="title" title="A Title with a Text Under" titleClass="mb-3">
        <Button variant="primary" type="button" onClick={() => MySwal.fire({
        title: 'The Internet?',
        text: 'That thing is still around?',
        icon: 'question',
        customClass: {
          confirmButton: `btn btn-primary w-xs mt-2`
        }
      })}>
          Click me
        </Button>
      </ComponentContainerCard>

      <ComponentContainerCard id="message" title="Message" titleClass="mb-3">
        <div className="hstack gap-2">
          <Button variant="success" onClick={() => MySwal.fire({
          title: 'Good job!',
          text: 'You clicked the button!',
          icon: 'success',
          showCancelButton: true,
          customClass: {
            confirmButton: `btn btn-primary w-xs mt-2`,
            cancelButton: 'btn btn-danger w-xs mt-2'
          },
          buttonsStyling: false,
          showCloseButton: false
        })}>
            Success
          </Button>
          <Button variant="warning" onClick={() => MySwal.fire({
          title: 'Oops...',
          text: 'Something went wrong!',
          icon: 'warning',
          customClass: {
            confirmButton: `btn btn-primary w-xs mt-2`
          },
          buttonsStyling: false,
          footer: '<a href="">Why do I have this issue?</a>',
          showCloseButton: false
        })}>
            Warning
          </Button>
          <Button variant="info" onClick={() => MySwal.fire({
          title: 'Oops...',
          text: 'Something went wrong!',
          icon: 'info',
          customClass: {
            confirmButton: `btn btn-primary w-xs mt-2`
          },
          buttonsStyling: false,
          footer: '<a href="">Why do I have this issue?</a>',
          showCloseButton: false
        })}>
            Info
          </Button>
          <Button variant="danger" onClick={() => MySwal.fire({
          title: 'Oops...',
          text: 'Something went wrong!',
          icon: 'error',
          customClass: {
            confirmButton: `btn btn-primary w-xs mt-2`
          },
          buttonsStyling: false,
          footer: '<a href="">Why do I have this issue?</a>',
          showCloseButton: false
        })}>
            Error
          </Button>
        </div>
      </ComponentContainerCard>

      <ComponentContainerCard id="longcontent" title="Long content Images Message" titleClass="mb-3">
        <Button variant="primary" onClick={() => MySwal.fire({
        imageUrl: 'https://placeholder.pics/svg/300x1500',
        imageHeight: 1500,
        imageAlt: 'A tall image',
        customClass: {
          confirmButton: `btn btn-primary w-xs mt-2`
        },
        buttonsStyling: false,
        showCloseButton: false
      })}>
          Click me
        </Button>
      </ComponentContainerCard>

      <ComponentContainerCard id="parameter" title="Parameter" titleClass="mb-3">
        <Button variant="primary" type="button" onClick={() => MySwal.fire({
        title: 'Are you sure?',
        text: "You won't be able to revert this!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'No, cancel!',
        customClass: {
          confirmButton: `btn btn-primary w-xs mt-2`,
          cancelButton: 'btn btn-danger w-xs mt-2'
        },
        buttonsStyling: false,
        showCloseButton: false
      }).then(function (result) {
        if (result.value) {
          MySwal.fire({
            title: 'Deleted!',
            text: 'Your file has been deleted.',
            icon: 'success',
            customClass: {
              confirmButton: `btn btn-primary w-xs mt-2`
            },
            buttonsStyling: false
          });
        } else if (
        // Read more about handling dismissals
        result.dismiss === Swal.DismissReason.cancel) {
          MySwal.fire({
            title: 'Cancelled',
            text: 'Your imaginary file is safe :)',
            icon: 'error',
            customClass: {
              confirmButton: `btn btn-primary mt-2`
            },
            buttonsStyling: false
          });
        }
      })}>
          Click me
        </Button>
      </ComponentContainerCard>
    </>;
};
export default AllSweetAlerts;