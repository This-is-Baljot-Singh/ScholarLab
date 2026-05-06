/**
 * StudentManagementTable - Data table of enrolled students with attendance and risk
 * Displays Name, Attendance %, and Risk Level badge
 * Clicking a student opens StudentRiskModal with SHAP explanations
 */

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronDown,
  Search,
  AlertCircle,
  TrendingUp,
  Loader2,
} from 'lucide-react';
import { studentManagementAPI } from '@/api/facultyAPI';
import { StudentRiskModal } from './StudentRiskModal';
import { SkeletonLoader } from '@/shared/ui/SkeletonLoader';
import { cn } from '@/lib/utils';
import type { EnrolledStudent } from '@/types/faculty';

interface StudentManagementTableProps {
  courseId: string;
  onStudentSelect?: (student: EnrolledStudent) => void;
  maxRows?: number;
}

type SortField = 'name' | 'attendance' | 'risk';
type SortOrder = 'asc' | 'desc';

// Mock students for development
const MOCK_STUDENTS: EnrolledStudent[] = [
  {
    id: 'student-001',
    name: 'Alice Johnson',
    email: 'alice@university.edu',
    studentId: 'A001',
    enrolledCourses: ['CS101'],
    attendanceRate: 95,
    riskLevel: 'green',
    riskScore: 15,
    lastAttendance: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    recentFlags: 0,
    avgEngagement: 92,
  },
  {
    id: 'student-002',
    name: 'Bob Smith',
    email: 'bob@university.edu',
    studentId: 'A002',
    enrolledCourses: ['CS101'],
    attendanceRate: 78,
    riskLevel: 'yellow',
    riskScore: 52,
    lastAttendance: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    recentFlags: 1,
    avgEngagement: 65,
  },
  {
    id: 'student-003',
    name: 'Charlie Davis',
    email: 'charlie@university.edu',
    studentId: 'A003',
    enrolledCourses: ['CS101'],
    attendanceRate: 45,
    riskLevel: 'red',
    riskScore: 78,
    lastAttendance: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
    recentFlags: 3,
    avgEngagement: 28,
  },
  {
    id: 'student-004',
    name: 'Diana Wilson',
    email: 'diana@university.edu',
    studentId: 'A004',
    enrolledCourses: ['CS101'],
    attendanceRate: 88,
    riskLevel: 'green',
    riskScore: 22,
    lastAttendance: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    recentFlags: 0,
    avgEngagement: 85,
  },
  {
    id: 'student-005',
    name: 'Emma Martinez',
    email: 'emma@university.edu',
    studentId: 'A005',
    enrolledCourses: ['CS101'],
    attendanceRate: 72,
    riskLevel: 'yellow',
    riskScore: 48,
    lastAttendance: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    recentFlags: 2,
    avgEngagement: 58,
  },
];

export const StudentManagementTable: React.FC<StudentManagementTableProps> = ({
  courseId,
  onStudentSelect,
  maxRows = 10,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('risk');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedStudent, setSelectedStudent] = useState<EnrolledStudent | null>(null);
  const [showRiskModal, setShowRiskModal] = useState(false);

  // Fetch students
  const { data: enrollmentData, isLoading, error } = useQuery({
    queryKey: ['students', 'enrolled', courseId],
    queryFn: () => studentManagementAPI.getStudentsSummary(courseId),
    staleTime: 1000 * 60, // 1 minute
    retry: 1,
  });

  const students = useMemo(() => {
    const baseStudents = enrollmentData || MOCK_STUDENTS;

    // Filter by search term
    let filtered = baseStudents;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = baseStudents.filter(
        (s) =>
          s.name.toLowerCase().includes(term) ||
          s.email.toLowerCase().includes(term) ||
          s.studentId.toLowerCase().includes(term)
      );
    }

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      switch (sortField) {
        case 'name':
          aVal = a.name;
          bVal = b.name;
          break;
        case 'attendance':
          aVal = a.attendanceRate;
          bVal = b.attendanceRate;
          break;
        case 'risk':
          aVal = a.riskScore;
          bVal = b.riskScore;
          break;
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return sorted.slice(0, maxRows);
  }, [enrollmentData, searchTerm, sortField, sortOrder, maxRows]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const handleStudentClick = (student: EnrolledStudent) => {
    setSelectedStudent(student);
    setShowRiskModal(true);
    onStudentSelect?.(student);
  };

  const getRiskBadgeColor = (
    riskLevel: string
  ): string => {
    switch (riskLevel) {
      case 'green':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'yellow':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'red':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  if (isLoading && !enrollmentData) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-slate-900">Enrolled Students</h3>
        <div className="space-y-3">
          <SkeletonLoader height="h-12" count={5} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900">Failed to load students</h3>
            <p className="mt-1 text-sm text-red-700">
              Could not fetch enrolled students. Using mock data.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {/* Header */}
        <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Enrolled Students</h3>
              <p className="mt-1 text-sm text-slate-600">
                {students.length} of {enrollmentData?.length || MOCK_STUDENTS.length} students
              </p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="border-b border-slate-200 px-6 py-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, email, or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-10 pr-4 text-sm placeholder-slate-500 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left">
                  <button
                    onClick={() => handleSort('name')}
                    className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-700 hover:text-slate-900 transition"
                  >
                    Name
                    {sortField === 'name' && (
                      <ChevronDown
                        className={cn(
                          'h-4 w-4 transition-transform',
                          sortOrder === 'asc' && 'rotate-180'
                        )}
                      />
                    )}
                  </button>
                </th>
                <th className="px-6 py-3 text-left">
                  <span className="text-xs font-semibold uppercase tracking-widest text-slate-700">
                    Email
                  </span>
                </th>
                <th className="px-6 py-3 text-left">
                  <button
                    onClick={() => handleSort('attendance')}
                    className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-700 hover:text-slate-900 transition"
                  >
                    Attendance
                    {sortField === 'attendance' && (
                      <ChevronDown
                        className={cn(
                          'h-4 w-4 transition-transform',
                          sortOrder === 'asc' && 'rotate-180'
                        )}
                      />
                    )}
                  </button>
                </th>
                <th className="px-6 py-3 text-left">
                  <button
                    onClick={() => handleSort('risk')}
                    className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-700 hover:text-slate-900 transition"
                  >
                    Risk Level
                    {sortField === 'risk' && (
                      <ChevronDown
                        className={cn(
                          'h-4 w-4 transition-transform',
                          sortOrder === 'asc' && 'rotate-180'
                        )}
                      />
                    )}
                  </button>
                </th>
                <th className="px-6 py-3 text-left">
                  <span className="text-xs font-semibold uppercase tracking-widest text-slate-700">
                    Action
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr
                  key={student.id}
                  className="border-b border-slate-100 hover:bg-slate-50 transition cursor-pointer"
                  onClick={() => handleStudentClick(student)}
                >
                  <td className="px-6 py-4">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{student.name}</p>
                      <p className="text-xs text-slate-500">#{student.studentId}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm text-slate-600">{student.email}</p>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full transition-all',
                            student.attendanceRate >= 80
                              ? 'bg-green-500'
                              : student.attendanceRate >= 60
                                ? 'bg-amber-500'
                                : 'bg-red-500'
                          )}
                          style={{ width: `${student.attendanceRate}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-slate-900 w-12">
                        {student.attendanceRate}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold',
                        getRiskBadgeColor(student.riskLevel)
                      )}
                    >
                      {student.riskLevel === 'green'
                        ? '✓ Low'
                        : student.riskLevel === 'yellow'
                          ? '⚠ Medium'
                          : '✕ High'}
                      {' '}
                      ({student.riskScore})
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStudentClick(student);
                      }}
                      className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-700 transition"
                    >
                      View details
                      <ChevronDown className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {students.length === 0 && (
          <div className="flex flex-col items-center justify-center px-6 py-12">
            <Search className="h-12 w-12 text-slate-300 mb-3" />
            <p className="text-slate-600 font-medium">No students found</p>
            <p className="text-sm text-slate-500">Try adjusting your search criteria</p>
          </div>
        )}
      </div>

      {/* Student Risk Modal */}
      {selectedStudent && (
        <StudentRiskModal
          isOpen={showRiskModal}
          studentId={selectedStudent.id}
          studentName={selectedStudent.name}
          riskScore={selectedStudent.riskScore}
          onClose={() => {
            setShowRiskModal(false);
            setSelectedStudent(null);
          }}
        />
      )}
    </>
  );
};
