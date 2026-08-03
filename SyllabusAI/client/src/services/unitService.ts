import api from './api';

export interface Unit {
  id: number;
  subjectId: number;
  unitNumber: number;
  name: string;
  description?: string;
  materialCount?: number;
}

const unitService = {
  async getUnitsBySubject(subjectId: number): Promise<Unit[]> {
    const response = await api.get<{ units: Unit[] }>(`/subjects/${subjectId}/units`);
    return response.data.units;
  },

  async getUnitById(id: number): Promise<Unit & { materials: any[] }> {
    const response = await api.get(`/units/${id}`);
    return response.data.unit;
  },
};

export default unitService;
