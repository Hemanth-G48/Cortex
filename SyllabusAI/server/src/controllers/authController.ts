import { Request, Response } from 'express';
import jwt, { SignOptions } from 'jsonwebtoken';
import { User, Institution, Course } from '../models';
import admin from '../config/firebase';

const generateToken = (user: User): string => {
  const options: SignOptions = {
    expiresIn: '7d',
  };
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role },
    process.env.JWT_SECRET || 'fallback-secret',
    options
  );
};

export const register = async (req: Request, res: Response): Promise<void> => {
  try {
    const { email, password, firstName, lastName, institutionId, courseId } = req.body;

    if (!email || !password || !firstName || !lastName) {
      res.status(400).json({ message: 'All fields are required' });
      return;
    }

    const existingUser = await User.findOne({ where: { email } });
    if (existingUser) {
      res.status(400).json({ message: 'Email already registered' });
      return;
    }

    // Validate institution exists and is active (admin-approved)
    if (institutionId) {
      const institution = await Institution.findByPk(institutionId);
      if (!institution || !institution.isActive) {
        res.status(400).json({ message: 'Invalid or unapproved institution' });
        return;
      }
    }

    // Validate course belongs to the selected institution
    if (courseId) {
      const course = await Course.findByPk(courseId);
      if (!course || (institutionId && course.institutionId !== parseInt(institutionId))) {
        res.status(400).json({ message: 'Invalid course for selected institution' });
        return;
      }
    }

    const user = await User.create({
      email,
      password,
      firstName,
      lastName,
      institutionId: institutionId || null,
      courseId: courseId || null,
    });

    const token = generateToken(user);

    res.status(201).json({
      message: 'User registered successfully',
      user: user.toJSON(),
      token,
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ message: 'Error registering user' });
  }
};

export const login = async (req: Request, res: Response): Promise<void> => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      res.status(400).json({ message: 'Email and password are required' });
      return;
    }

    const user = await User.findOne({ where: { email } });
    if (!user) {
      res.status(401).json({ message: 'Invalid credentials' });
      return;
    }

    if (!user.isActive) {
      res.status(401).json({ message: 'Account is deactivated' });
      return;
    }

    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      res.status(401).json({ message: 'Invalid credentials' });
      return;
    }

    const token = generateToken(user);

    res.json({
      message: 'Login successful',
      user: user.toJSON(),
      token,
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ message: 'Error logging in' });
  }
};

export const getProfile = async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({ message: 'Not authenticated' });
      return;
    }

    // Fetch user with institution and course info
    const user = await User.findByPk(req.user.id, {
      include: [
        { model: Institution, as: 'institution', attributes: ['id', 'name', 'shortName'] },
        { model: Course, as: 'course', attributes: ['id', 'name', 'code', 'duration'] },
      ],
    });

    res.json({ user: user?.toJSON() });
  } catch (error) {
    console.error('Get profile error:', error);
    res.status(500).json({ message: 'Error fetching profile' });
  }
};

export const updateProfile = async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({ message: 'Not authenticated' });
      return;
    }

    const { firstName, lastName } = req.body;

    await req.user.update({ firstName, lastName });

    res.json({
      message: 'Profile updated successfully',
      user: req.user.toJSON(),
    });
  } catch (error) {
    console.error('Update profile error:', error);
    res.status(500).json({ message: 'Error updating profile' });
  }
};

export const googleAuth = async (req: Request, res: Response): Promise<void> => {
  try {
    const { idToken } = req.body;

    if (!idToken) {
      res.status(400).json({ message: 'Firebase ID token is required' });
      return;
    }

    // Verify the Firebase ID token
    const decodedToken = await admin.auth().verifyIdToken(idToken);
    const { uid, email, name } = decodedToken;

    if (!email) {
      res.status(400).json({ message: 'Email not available from Google account' });
      return;
    }

    // Check if user exists by firebaseUid or email
    let user = await User.findOne({
      where: { firebaseUid: uid },
    });

    if (!user) {
      user = await User.findOne({ where: { email } });

      if (user) {
        // Existing email/password user — link their Google account
        await user.update({ firebaseUid: uid, authProvider: 'google' });
      } else {
        // New user — create account
        const nameParts = (name || email.split('@')[0]).split(' ');
        const firstName = nameParts[0] || 'User';
        const lastName = nameParts.slice(1).join(' ') || '';

        user = await User.create({
          email,
          password: '',
          firstName,
          lastName,
          firebaseUid: uid,
          authProvider: 'google',
        });
      }
    }

    if (!user.isActive) {
      res.status(401).json({ message: 'Account is deactivated' });
      return;
    }

    const token = generateToken(user);

    // Fetch full user with associations
    const fullUser = await User.findByPk(user.id, {
      include: [
        { model: Institution, as: 'institution', attributes: ['id', 'name', 'shortName'] },
        { model: Course, as: 'course', attributes: ['id', 'name', 'code', 'duration'] },
      ],
    });

    res.json({
      message: 'Google authentication successful',
      user: fullUser?.toJSON(),
      token,
    });
  } catch (error) {
    console.error('Google auth error:', (error as Error).message || error);
    res.status(401).json({ message: 'Google authentication failed: ' + ((error as Error).message || 'Unknown error') });
  }
};

export const completeProfile = async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({ message: 'Not authenticated' });
      return;
    }

    const { firstName, lastName, institutionId, courseId } = req.body;

    if (!institutionId || !courseId) {
      res.status(400).json({ message: 'Institution and course are required' });
      return;
    }

    // Validate institution exists and is active
    const institution = await Institution.findByPk(institutionId);
    if (!institution || !institution.isActive) {
      res.status(400).json({ message: 'Invalid or unapproved institution' });
      return;
    }

    // Validate course belongs to the selected institution
    const course = await Course.findByPk(courseId);
    if (!course || course.institutionId !== parseInt(institutionId)) {
      res.status(400).json({ message: 'Invalid course for selected institution' });
      return;
    }

    const updateData: Record<string, unknown> = { institutionId, courseId };
    if (firstName) updateData.firstName = firstName;
    if (lastName) updateData.lastName = lastName;

    await req.user.update(updateData);

    const fullUser = await User.findByPk(req.user.id, {
      include: [
        { model: Institution, as: 'institution', attributes: ['id', 'name', 'shortName'] },
        { model: Course, as: 'course', attributes: ['id', 'name', 'code', 'duration'] },
      ],
    });

    res.json({
      message: 'Profile completed successfully',
      user: fullUser?.toJSON(),
    });
  } catch (error) {
    console.error('Complete profile error:', error);
    res.status(500).json({ message: 'Error completing profile' });
  }
};

export const changePassword = async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({ message: 'Not authenticated' });
      return;
    }

    const { currentPassword, newPassword } = req.body;

    if (!currentPassword || !newPassword) {
      res.status(400).json({ message: 'Current and new password are required' });
      return;
    }

    const isPasswordValid = await req.user.comparePassword(currentPassword);
    if (!isPasswordValid) {
      res.status(401).json({ message: 'Current password is incorrect' });
      return;
    }

    await req.user.update({ password: newPassword });

    res.json({ message: 'Password changed successfully' });
  } catch (error) {
    console.error('Change password error:', error);
    res.status(500).json({ message: 'Error changing password' });
  }
};
