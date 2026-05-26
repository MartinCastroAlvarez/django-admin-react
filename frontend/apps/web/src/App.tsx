import { Route, Routes } from 'react-router-dom';

import { Layout } from './Layout';
import { HomePage } from './pages/HomePage';
import { ListPage } from './pages/ListPage';
import { DetailPage } from './pages/DetailPage';

export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path=":appLabel/:modelName" element={<ListPage />} />
        <Route path=":appLabel/:modelName/:pk" element={<DetailPage />} />
        <Route
          path="*"
          element={<div className="p-6 text-sm text-gray-500">Page not found.</div>}
        />
      </Routes>
    </Layout>
  );
}
