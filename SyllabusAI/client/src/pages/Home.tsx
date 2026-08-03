import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const features = [
  {
    title: 'Organized by Semester',
    description: 'Materials structured by institution, course, subject, and unit. Find exactly what you need.',
    icon: '📚',
    color: 'bg-blue-50 text-blue-600',
  },
  {
    title: 'AI-Powered Summaries',
    description: 'Get instant AI summaries of any unit or combine multiple units for comprehensive reviews.',
    icon: '🤖',
    color: 'bg-purple-50 text-purple-600',
  },
  {
    title: 'Smart Quizzes',
    description: 'Test your knowledge with AI-generated quizzes tailored to your study materials.',
    icon: '🧠',
    color: 'bg-green-50 text-green-600',
  },
  {
    title: 'Easy Downloads',
    description: 'Download PDFs, presentations, and notes with a single click. Study offline anytime.',
    icon: '📥',
    color: 'bg-amber-50 text-amber-600',
  },
];

export function Home() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary/5 via-white to-secondary/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-3xl mx-auto"
          >
            <h1 className="text-4xl sm:text-6xl font-bold text-text leading-tight">
              Study Smarter with{' '}
              <span className="text-primary">AI-Powered</span>{' '}
              Learning
            </h1>
            <p className="mt-6 text-lg text-text-secondary leading-relaxed">
              Access curated study materials, generate AI summaries, and test yourself with smart quizzes.
              All organized by your college, course, and semester.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/register"
                className="inline-flex items-center justify-center px-8 py-3.5 bg-primary text-white font-semibold rounded-xl hover:bg-primary-dark transition-all shadow-lg shadow-primary/25 no-underline"
              >
                Get Started Free
              </Link>
              <Link
                to="/browse"
                className="inline-flex items-center justify-center px-8 py-3.5 bg-white text-text font-semibold rounded-xl border border-border hover:border-primary hover:text-primary transition-all no-underline"
              >
                Browse Materials
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-text">Everything you need to ace your exams</h2>
            <p className="mt-4 text-text-secondary">Powerful tools designed for students, by students.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                viewport={{ once: true }}
                className="p-6 rounded-2xl border border-border hover:border-primary/30 hover:shadow-lg transition-all group"
              >
                <div className={`w-12 h-12 rounded-xl ${feature.color} flex items-center justify-center text-2xl mb-4`}>
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-text mb-2">{feature.title}</h3>
                <p className="text-sm text-text-secondary leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-gradient-to-r from-primary to-primary-dark">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to start learning?</h2>
          <p className="text-white/80 mb-8 text-lg">Join your classmates and get access to all study materials.</p>
          <Link
            to="/register"
            className="inline-flex items-center justify-center px-8 py-3.5 bg-white text-primary font-semibold rounded-xl hover:bg-gray-50 transition-all no-underline"
          >
            Create Free Account
          </Link>
        </div>
      </section>
    </div>
  );
}
