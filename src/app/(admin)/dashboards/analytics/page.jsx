import PageTitle from '@/components/PageTitle';
import { Row } from 'react-bootstrap';
import dynamic from 'next/dynamic';
import BalanceCard from './components/BalanceCard';

const SalesChart = dynamic(() => import('./components/SalesChart'), { ssr: false });

const Statistics = dynamic(() => import('./components/Statistics'), { ssr: false });

export const metadata = {
  title: 'Analytics'
};
const AnalyticsPage = () => {
  return <>
    <PageTitle title="Thống kê" subName="Dashboard" />
    <Statistics />
    <Row>
      <SalesChart />
      <BalanceCard />
    </Row>


  </>;
};
export default AnalyticsPage;