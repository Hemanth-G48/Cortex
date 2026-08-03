import api from './api';

export interface Subject {
  id: number;
  courseId: number;
  name: string;
  code: string;
  semester: number;
  credits: number;
  description?: string;
  unitCount?: number;
}

const subjectService = {
  async getSubjectsByCourse(courseId: number): Promise<Subject[]> {
    const response = await api.get<{ subjects: Subject[] }>(`/courses/${courseId}/subjects`);
    return response.data.subjects;
  },

  async getSubjectById(id: number): Promise<Subject & { units: any[] }> {
    const response = await api.get(`/subjects/${id}`);
    return response.data.subject;
  },
};

export default subjectService;
