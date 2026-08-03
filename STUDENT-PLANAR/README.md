<div align="center">
  <h1>🎓 Student Planar</h1>
  <p>
    <strong>A full-stack MERN application for modern schedule and course management.</strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB" />
    <img src="https://img.shields.io/badge/Express.js-000000?style=for-the-badge&logo=express&logoColor=white" alt="Express" />
    <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
    <img src="https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node.js" />
    <img src="https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E" alt="Vite" />
  </p>
</div>

<br />

## 🌟 Overview

**Student Planar** is a robust role-based scheduling and task management platform. Built on the MERN stack and optimized with Vite, it provides distinct, secure dashboards for Teachers and Students—making academic coordination and task tracking completely seamless. 

With its modern, futuristic UI and robust scalable backend, Student Planar is designed to streamline academic administrative duties and ensure students remain on track.

## 🚀 Key Features

- 🔐 **Role-Based dashboards:** Dedicated views and permissions for 'Teachers' and 'Students'.
- 📚 **Course Management:** Teachers can securely create, edit, and assign courses.
- 📁 **File-Based Assignments:** Teachers assign homework and coursework by uploading files (PDFs, Word docs, images, txt files, etc.).
- 📥 **Interactive Downloading:** Students can download assignment files directly from their task view with a custom, theme-integrated download interface.
- 🕒 **Schedule & Task Tracking:** Intuitive daily scheduling, real-time date-restrictions, and calendar syncs.
- 💅 **Immersive UI:** A rich, responsive UI utilizing dynamic layouts and modern styling constraints.
- 🛡️ **Secure Authentication:** JWT-based user authentication and robust password hashing.

## 📁 Project Structure

This is a monorepo-style setup containing both the Frontend (`client`) and the Backend (`server`).

```text
STUDENT-PLANAR/
├── client/              # React frontend (Vite)
│   ├── src/             # Source files, Components, Views
│   ├── public/          # Static assets
│   └── package.json     # Client dependencies
├── server/              # Node.js/Express backend
│   ├── models/          # Mongoose DB Schemas
│   ├── routes/          # Express API Endpoints
│   ├── uploads/         # Local file storage
│   ├── server.js        # Entry point for backend
│   └── package.json     # Server dependencies
├── .gitignore           # Shared Git Ignore configurations
└── README.md            # This file
```

## ⚙️ Local Development Setup

To run this project locally, ensure you have **Node.js** (v16+) and **MongoDB** installed on your workstation.

### 1. Clone the repository
```bash
git clone https://github.com/HimanshuKumarRout/student-planar.git
cd student-planar
```

### 2. Configure the Backend (Server)
```bash
# Navigate to the server folder
cd server

# Install backend dependencies
npm install

# Create environment variables
# Duplicate .env.example into .env or create a new .env file with the following:
# PORT=5000
# MONGODB_URI=your_mongodb_connection_string
# JWT_SECRET=your_super_secret_key

# Start the development server
node server.js
```
*The server should now be running on `http://localhost:5000`.*

### 3. Configure the Frontend (Client)
Open a new terminal window or tab to keep the server running.
```bash
# From the root directory, navigate to the client folder
cd client

# Install frontend dependencies
npm install

# Start the Vite development server
npm run dev
```
*The client app should now be running and accessible at `http://localhost:5173` (default).*

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check the [issues page](https://github.com/HimanshuKumarRout/student-planar/issues) to see what we're working on.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## 👨‍💻 Author

**Himanshu Kumar Rout**

* GitHub: [https://github.com/HimanshuKumarRout](https://github.com/HimanshuKumarRout)
* Email: [himanshurout136@gmail.com](mailto:himanshurout136@gmail.com)


## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---
<p align="center">Made with ❤️ for better academic productivity.</p>
