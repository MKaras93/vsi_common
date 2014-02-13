""" Utility classes for modeling cameras """
import numpy as np


def construct_K(focal_len, image_size):
    """ create calibration matrix K using the focal length and image.size
    Assumes 0 skew and principal point at center of image
    Note that image_size = (width, height) """
    K = np.array([[focal_len, 0, image_size[0]/2.0], [0, focal_len, image_size[1]/2.0], [0, 0, 1]])
    return K


class PinholeCamera(object):
    """ Models a pinhole camera, i.e. one with a single center of projection and no lens distortion """
    def __init__(self, K, R, T):
        self.K = K
        self.R = R
        self.T = T
        # compute projection matrix
        self.P = np.dot( K, np.hstack((R, T.reshape(3, 1))) )
        # normalize s.t. P[3,4] = 1
        if abs(self.P[2,3]) > 1e-6:
            self.P /= self.P[2,3]
        # compute and store camera center
        self.center = np.dot(-R.transpose(), T)
        # compute inverse projection matrix for backprojection
        self.Kinv = np.linalg.inv(K)
        self.KRinv = np.dot(R.transpose(), self.Kinv)

    def viewing_rays(self, pts_2d):
        """ backproject the 2d image points to unit ray directions (with origin at camera center) """
        N = len(pts_2d)
        pts_2d_h_np = np.hstack((np.array(pts_2d), np.ones((N,1))))  # create an Nx3 numpy array
        rays_np = np.dot(self.KRinv, pts_2d_h_np.T)
        ray_lens = np.sqrt((rays_np * rays_np).sum(0))
        unit_rays = rays_np / ray_lens  # use broadcasting to divide by magnitudes
        unit_rays_list = [unit_rays[:,i] for i in range(N)]
        return unit_rays_list

    def backproject_points_plane(self, pts_2d, plane):
        """ backproject a point onto a 3-d plane """
        unit_rays = np.array(self.viewing_rays(pts_2d)).T
        depths = -np.dot(plane, np.append(self.center,1)) / np.dot(plane[0:3], unit_rays)
        pts_3d_np = self.center.reshape((3,1)) + unit_rays * depths
        pts_3d = [pts_3d_np[:,i] for i in range(len(pts_2d))]

        return pts_3d

    def backproject_point_plane(self, pt_2d, plane):
        """ backproject a point onto a 3-d plane """
        pts = self.backproject_points_plane((pt_2d,), plane)
        return pts[0]

    def backproject_points(self, pts_2d, depths):
        """ backproject a point given camera params, image position, and depth """
        N = len(depths)
        if not len(pts_2d) == len(depths):
            raise Exception('number of points %d != number of depths %d' % (len(pts_2d),len(depths)))
        unit_rays = np.array(self.viewing_rays(pts_2d)).T
        pts_3d_np = self.center.reshape((3,1)) + unit_rays * np.array(depths)
        pts_3d = [pts_3d_np[:,i] for i in range(N)]

        return pts_3d

    def backproject_point(self, pt_2d, depth):
        """ convenience wrapper around backproject_points """
        pts = self.backproject_points((pt_2d,), (depth,))
        return pts[0]

    def project_vectors(self, vecs_3d):
        """ compute projection matrix from K,R,T and project vecs_3d into image coordinates """
        num_vecs = len(vecs_3d)
        # create 3xN matrix from set of 3d vectors
        vecs_3d_m = np.array(vecs_3d).transpose()
        # convert to homogeneous coordinates
        vecs_3d_m_h = np.vstack((vecs_3d_m, np.zeros((1, num_vecs))))
        vecs_2d_m_h = np.dot(self.P, vecs_3d_m_h)
        #vecs_2d = [vecs_2d_m_h[0:2, c] / vecs_2d_m_h[2, c] for c in range(num_vecs)]
        vecs_2d = [col[0:2] / col[2] for col in vecs_2d_m_h.transpose()]
        return vecs_2d

    def project_vector(self, vecs_3d):
        """ convenience wrapper around project_vectors """
        pts = self.project_vectors((vecs_3d,))
        return pts[0]

    def project_points(self, pts_3d):
        """ compute projection matrix from K,R,T and project pts_3d into image coordinates """
        num_pts = len(pts_3d)
        # create 3xN matrix from set of 3d points
        pts_3d_m = np.array(pts_3d).transpose()
        # convert to homogeneous coordinates
        pts_3d_m_h = np.vstack((pts_3d_m, np.ones((1, num_pts))))
        pts_2d_m_h = np.dot(self.P, pts_3d_m_h)
        #pts_2d = [pts_2d_m_h[0:2, c] / pts_2d_m_h[2, c] for c in range(num_pts)]
        pts_2d = [col[0:2] / col[2] for col in pts_2d_m_h.transpose()]
        return pts_2d

    def project_point(self, pt_3d):
        """ convenience wrapper around project_points """
        pts = self.project_points((pt_3d,))
        return pts[0]

    def plane2image(self, plane_origin, plane_x, plane_y):
        """ compute the transformation from points on a 3-d plane to image coordinates
        """
        plane_xlen = np.sqrt(np.dot(plane_x, plane_x))
        plane_ylen = np.sqrt(np.dot(plane_y, plane_y))
        plane_xu = plane_x / plane_xlen
        plane_yu = plane_y / plane_ylen
        plane_normal = np.cross(plane_xu, plane_yu)
        plane2world_R = np.vstack((plane_xu, plane_yu, plane_normal)).transpose()
        plane2world_T = plane_origin
        plane_xy_scale = np.eye(4)
        np.fill_diagonal(plane_xy_scale, (plane_xlen, plane_ylen, 1.0, 1.0))
        plane2world_RT = np.vstack((np.hstack((plane2world_R, plane2world_T.reshape(3,1))),np.array((0,0,0,1))))
        plane2world = np.dot(plane2world_RT, plane_xy_scale)

        plane2img = np.dot(self.P, plane2world)
        # we can remove the 3rd column since the "Z" coordinates of points on the plane are 0
        plane2img3x3 = plane2img[:,(0,1,3)]
        return plane2img3x3

    def image2plane(self, plane_origin, plane_x, plane_y):
        """ compute the transformation from image coordinates to points on a 3-d plane
        """
        #plane_xlen = np.sqrt(np.dot(plane_x, plane_x))
        #plane_ylen = np.sqrt(np.dot(plane_y, plane_y))
        #plane_xu = plane_x / plane_xlen
        #plane_yu = plane_y / plane_ylen
        #plane_normal = np.cross(plane_xu, plane_yu)
        #world2plane_R = np.vstack((plane_xu, plane_yu, plane_normal))
        #world2plane_T = -np.dot(world2plane_R, plane_origin)
        #world2plane = np.vstack((np.hstack((world2plane_R, world2plane_T.reshape(3,1))),np.array((0,0,0,1))))

        #cam2world_R = self.R.transpose()
        #cam2world_T = -np.dot(cam2world_R, self.T)
        #cam2world = np.vstack((np.hstack((cam2world_R, cam2world_T.reshape(3,1))),np.array((0,0,0,1))))
        #Kinv4x3 = np.vstack((self.Kinv, np.zeros((1,3))))

        #img2plane = np.dot(np.dot(world2plane, cam2world), Kinv4x3)
        ## since the "Z" coordinate of the plane is 0, we can remove the 3rd row of the transform
        ## make a deep copy so that matrix is contiguous
        #img2plane3x3 = img2plane[(0,1,3),:].copy()

        #return img2plane3x3
        p2i = self.plane2image(plane_origin, plane_x, plane_y)
        return np.linalg.inv(p2i)

    def rescale(self, scale_factor):
        """ Return a new camera corresponding to a resampled image
            Note: leaves calling object unmodified.
        """
        Knew = self.K * scale_factor
        Knew[2,2] = self.K[2,2]
        return PinholeCamera(Knew, self.R, self.T)

    def principal_point(self):
        """ return the principal point (image coordinates) """
        return self.K[0:2,2]

    def principal_ray(self):
        """ compute and return the camera's principal ray """
        return self.R[2,:]

    def x_axis(self):
        """ compute and return the camera's x axis """
        return self.R[0,:]

    def y_axis(self):
        """ compute and return the camera's x axis """
        return self.R[1,:]

    def saveas_KRT(self, filename):
        """ write the K,R,T matrices to an ascii text file """
        with open(filename, 'w') as fd:
            # write intrinsics K matrix
            for row in self.K:
                fd.write('%f %f %f\n' % (row[0],row[1],row[2]))
            fd.write('\n')
            # write rotation matrix
            for row in self.R:
                fd.write('%f %f %f\n' % (row[0],row[1],row[2]))
            fd.write('\n')
            # write translation vector
            fd.write('%f %f %f\n' % (self.T[0],self.T[1],self.T[2]))
        return

    def saveas_P(self, filename):
        """ write the projection matrix to an ascii text file """
        with open(filename, 'w') as fd:
            # write intrinsics K matrix
            for row in self.P:
                fd.write('%f %f %f %f\n' % (row[0],row[1],row[2],row[3]))
        return


def triangulate_point(cameras, projections):
    """ Triangulate a 3-d point given it's projection in two images """
    num_obs = len(cameras)
    if len(projections) != num_obs:
        raise Exception('Expecting same number of cameras and 2-d projections')

    A = np.zeros((2*num_obs,4))
    for i in range(num_obs):
        A[2*i,:] = cameras[i].P[0,:] - cameras[i].P[2,:]*projections[i][0]
        A[2*i + 1,:] = cameras[i].P[1,:] - cameras[i].P[2,:]*projections[i][1]

    _, _, Vh = np.linalg.svd(A)
    V = Vh.conj().transpose()

    point = V[:,-1]

    return point


