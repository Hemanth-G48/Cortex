import api from './api';

export interface Material {
  id: number;
  unitId: number;
  uploadedById: number;
  title: string;
  description?: string;
  fileType: string;
  fileUrl: string;
  fileSize: number;
  originalFileName: string;
  viewCount: number;
  downloadCount: number;
}

const materialService = {
  async getMaterialsByUnit(unitId: number): Promise<Material[]> {
    const response = await api.get<{ materials: Material[] }>(`/units/${unitId}/materials`);
    return response.data.materials;
  },

  async uploadMaterial(unitId: number, formData: FormData): Promise<Material> {
    const response = await api.post<{ material: Material }>(`/units/${unitId}/materials`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data.material;
  },

  getDownloadUrl(materialId: number): string {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
    return `${baseUrl}/materials/${materialId}/download`;
  },
};

export default materialService;
