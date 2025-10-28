// Dynamic import FullCalendar để giảm bundle size
import dynamic from 'next/dynamic';

// Chỉ import FullCalendar khi cần thiết
const FullCalendar = dynamic(() => import('@fullcalendar/react'), { 
  ssr: false,
  loading: () => <div>Loading calendar...</div>
});

// Import plugins một cách lazy
const dayGridPlugin = dynamic(() => import('@fullcalendar/daygrid'), { ssr: false });
const interactionPlugin = dynamic(() => import('@fullcalendar/interaction'), { ssr: false });
const timeGridPlugin = dynamic(() => import('@fullcalendar/timegrid'), { ssr: false });
const listPlugin = dynamic(() => import('@fullcalendar/list'), { ssr: false });
const bootstrapPlugin = dynamic(() => import('@fullcalendar/bootstrap'), { ssr: false });
const Calendar = ({
  events,
  onDateClick,
  onDrop,
  onEventClick,
  onEventDrop
}) => {
  // You can modify these events as per your needs
  const handleDateClick = arg => {
    onDateClick(arg);
  };
  const handleEventClick = arg => {
    onEventClick(arg);
  };
  const handleDrop = arg => {
    onDrop(arg);
  };
  const handleEventDrop = arg => {
    onEventDrop(arg);
  };
  return <div className="mt-4 mt-lg-0">
      <div id="calendar">
        <FullCalendar initialView="dayGridMonth" plugins={[dayGridPlugin, interactionPlugin, timeGridPlugin, listPlugin, bootstrapPlugin]} themeSystem="bootstrap" bootstrapFontAwesome={false} handleWindowResize={true} slotDuration="00:15:00" slotMinTime="08:00:00" slotMaxTime="19:00:00" buttonText={{
        today: 'Today',
        month: 'Month',
        week: 'Week',
        day: 'Day',
        list: 'List',
        prev: 'Prev',
        next: 'Next'
      }} headerToolbar={{
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay,listMonth'
      }}
      // height={height - 200}
      dayMaxEventRows={1} editable={true} selectable={true} droppable={true} events={events} dateClick={handleDateClick} eventClick={handleEventClick} drop={handleDrop} eventDrop={handleEventDrop} />
      </div>
    </div>;
};
export default Calendar;