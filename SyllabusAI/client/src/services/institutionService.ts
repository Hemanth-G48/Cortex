import api from './api';

export interface Institution {
  id: number;
  name: string;
  shortName: string;
  description?: string;
  isActive: boolean;
}

export interface Course {
  id: number;
  institutionId: number;
  name: string;
  code: string;
  description?: string;
  duration: number;
}

const institutionService = {
  async getInstitutions(): Promise<Institution[]> {
    const response = await api.get<{ institutions: Institution[] }>('/institutions');
    return response.data.institutions;
  },

  async getAllInstitutions(): Promise<Institution[]> {
    const response = await api.get<{ institutions: Institution[] }>('/institutions/admin/all');
    return response.data.institutions;
  },

  async getInstitutionById(id: number): Promise<Institution & { courses: Course[] }> {
    const response = await api.get(`/institutions/${id}`);
    return response.data.institution;
  },

  async getCoursesByInstitution(institutionId: number): Promise<Course[]> {
    const response = await api.get<{ courses: Course[] }>(`/institutions/${institutionId}/courses`);
    return response.data.courses;
  },

  async createInstitution(data: { name: string; shortName: string; description?: string }): Promise<Institution> {
    const response = await api.post<{ institution: Institution }>('/institutions', data);
    return response.data.institution;
  },

  async updateInstitutionStatus(id: number, isActive: boolean): Promise<Institution> {
    const response = await api.patch<{ institution: Institution }>(`/institutions/${id}/status`, { isActive });
    return response.data.institution;
  },
};

export default institutionService;
