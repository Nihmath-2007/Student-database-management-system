/* Staff Dashboard Chart.js Manager */

let staffMarksBarChart = null;
let staffMarksPieChart = null;
let currentStaffDashboardData = null;

async function initStaffDashboard() {
    try {
        const res = await fetch('/staff/api/dashboard');
        currentStaffDashboardData = await res.json();

        const setEl = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        };

        setEl('staffKpiSubjects', currentStaffDashboardData.assigned_subjects_count || 0);
        setEl('staffKpiAvgMarks', `${currentStaffDashboardData.average_marks || 0}%`);

        // Populate dropdown
        const select = document.getElementById('staffSubjectSelect');
        const subjects = currentStaffDashboardData.subjects || [];

        if (!select) return;

        if (subjects.length === 0) {
            select.innerHTML = '<option value="">No subjects assigned</option>';
            return;
        }

        select.innerHTML = subjects.map(s => `<option value="${s.subjectid}">${s.subject_code} - ${s.subject_name}</option>`).join('');

        onStaffSubjectChange();

    } catch (e) {
        console.error('Error loading staff dashboard:', e);
    }
}

async function onStaffSubjectChange() {
    const select = document.getElementById('staffSubjectSelect');
    if (!select) return;
    const subId = select.value;
    if (!subId) return;

    // Update title with selected subject name
    const selectedOption = select.options[select.selectedIndex];
    const selectedText = selectedOption ? selectedOption.text : '';
    const subjectName = selectedText.includes(' - ') ? selectedText.split(' - ').slice(1).join(' - ') : selectedText;

    const headingNameEl = document.getElementById('staffSelectedSubjectName');
    if (headingNameEl) {
        headingNameEl.textContent = subjectName || 'Subject';
    }

    try {
        const res = await fetch(`/staff/api/subject/${subId}`);
        if (!res.ok) {
            console.error(`Failed to fetch subject details: ${res.statusText}`);
            return;
        }
        const data = await res.json();

        // 1. Group student marks: ONE bar per student
        const studentMap = new Map();

        (data.student_marks || []).forEach(m => {
            const sId = m.studentid;
            if (!studentMap.has(sId)) {
                studentMap.set(sId, {
                    id: sId,
                    name: m.name,
                    regno: m.regno,
                    scores: []
                });
            }
            const student = studentMap.get(sId);
            if (m.percentage !== null && m.percentage !== undefined && !isNaN(parseFloat(m.percentage))) {
                student.scores.push(parseFloat(m.percentage));
            }
        });

        const studentsWithMarks = [];
        const studentsNoData = [];

        studentMap.forEach(s => {
            if (s.scores.length > 0) {
                const sum = s.scores.reduce((a, b) => a + b, 0);
                s.percentage = Math.round((sum / s.scores.length) * 10) / 10;
                s.hasData = true;
                studentsWithMarks.push(s);
            } else {
                s.percentage = null;
                s.hasData = false;
                studentsNoData.push(s);
            }
        });

        // Sort students with marks from highest to lowest marks
        studentsWithMarks.sort((a, b) => b.percentage - a.percentage);

        // Assign ranks to students with marks
        let currentRank = 1;
        for (let i = 0; i < studentsWithMarks.length; i++) {
            if (i > 0 && studentsWithMarks[i].percentage < studentsWithMarks[i - 1].percentage) {
                currentRank = i + 1;
            }
            studentsWithMarks[i].rank = currentRank;
        }

        // Students with missing marks have rank 'N/A'
        studentsNoData.forEach(s => {
            s.rank = 'N/A';
        });

        // Combined: sorted marks first, then missing marks shown as gray bars at the end
        const sortedStudents = [...studentsWithMarks, ...studentsNoData];

        // Compute class average from students who have marks
        const classAvg = studentsWithMarks.length > 0
            ? Math.round((studentsWithMarks.reduce((acc, s) => acc + s.percentage, 0) / studentsWithMarks.length) * 10) / 10
            : (parseFloat(data.average_marks) || 0);

        // Prepare colors and values
        // Green for 75%+, amber for 50-75% (and >=40%), red below 40%, gray for missing marks
        const bgColors = [];
        const borderColors = [];
        const chartValues = [];

        sortedStudents.forEach(s => {
            if (!s.hasData || s.percentage === null) {
                bgColors.push('#9ca3af');
                borderColors.push('#6b7280');
                chartValues.push(3); // Small visible gray stub so it renders visibly without blank gaps
            } else if (s.percentage >= 75) {
                bgColors.push('#10b981');
                borderColors.push('#059669');
                chartValues.push(s.percentage);
            } else if (s.percentage >= 40) {
                bgColors.push('#f59e0b');
                borderColors.push('#d97706');
                chartValues.push(s.percentage);
            } else {
                bgColors.push('#ef4444');
                borderColors.push('#dc2626');
                chartValues.push(s.percentage);
            }
        });

        // Chart labels (used internally for tooltip indexing)
        const chartLabels = sortedStudents.map(s => s.name);

        const canvasM = document.getElementById('staffStudentMarksBar');
        const emptyStateEl = document.getElementById('staffChartEmptyState');

        if (canvasM) {
            if (sortedStudents.length === 0) {
                if (emptyStateEl) emptyStateEl.classList.remove('d-none');
                canvasM.style.display = 'none';
                if (staffMarksBarChart) {
                    staffMarksBarChart.destroy();
                    staffMarksBarChart = null;
                }
            } else {
                if (emptyStateEl) emptyStateEl.classList.add('d-none');
                canvasM.style.display = 'block';

                const ctxM = canvasM.getContext('2d');
                if (staffMarksBarChart) staffMarksBarChart.destroy();

                // Custom inline plugin for 2 dashed reference lines: Pass Mark (40%) and Class Average
                const referenceLinesPlugin = {
                    id: 'staffReferenceLines',
                    afterDatasetsDraw(chart) {
                        const { ctx, chartArea, scales } = chart;
                        if (!chartArea || !scales || !scales.y) return;
                        const { left, right, top, bottom } = chartArea;
                        const y = scales.y;

                        const drawHLine = (val, text, strokeColor, bgColor, textColor, alignRight) => {
                            if (val === null || val === undefined || isNaN(val) || val < 0 || val > 100) return;
                            const yPixel = y.getPixelForValue(val);
                            if (yPixel < top || yPixel > bottom) return;

                            ctx.save();
                            ctx.beginPath();
                            ctx.setLineDash([5, 4]);
                            ctx.strokeStyle = strokeColor;
                            ctx.lineWidth = 1.5;
                            ctx.moveTo(left, yPixel);
                            ctx.lineTo(right, yPixel);
                            ctx.stroke();
                            ctx.setLineDash([]);

                            // Draw label pill
                            ctx.font = '600 11px system-ui, -apple-system, sans-serif';
                            const metrics = ctx.measureText(text);
                            const padX = 7;
                            const pillW = metrics.width + padX * 2;
                            const pillH = 18;
                            const pillX = alignRight ? (right - pillW - 6) : (left + 6);
                            const pillY = yPixel - (pillH / 2);

                            ctx.fillStyle = bgColor;
                            ctx.strokeStyle = strokeColor;
                            ctx.lineWidth = 1;

                            if (ctx.roundRect) {
                                ctx.beginPath();
                                ctx.roundRect(pillX, pillY, pillW, pillH, 4);
                                ctx.fill();
                                ctx.stroke();
                            } else {
                                ctx.fillRect(pillX, pillY, pillW, pillH);
                                ctx.strokeRect(pillX, pillY, pillW, pillH);
                            }

                            ctx.fillStyle = textColor;
                            ctx.textBaseline = 'middle';
                            ctx.textAlign = 'left';
                            ctx.fillText(text, pillX + padX, yPixel);
                            ctx.restore();
                        };

                        // 1. Pass Mark line (40%)
                        drawHLine(40, 'Pass Mark (40%)', '#dc2626', '#fef2f2', '#b91c1c', false);

                        // 2. Class Average line
                        if (classAvg > 0) {
                            drawHLine(classAvg, `Class Average (${classAvg}%)`, '#2563eb', '#eff6ff', '#1d4ed8', true);
                        }
                    }
                };

                staffMarksBarChart = new Chart(ctxM, {
                    type: 'bar',
                    data: {
                        labels: chartLabels,
                        datasets: [{
                            label: 'Marks (%)',
                            data: chartValues,
                            backgroundColor: bgColors,
                            borderColor: borderColors,
                            borderWidth: 1,
                            borderRadius: 3,
                            maxBarThickness: 28,
                            categoryPercentage: 0.85,
                            barPercentage: 0.95
                        }]
                    },
                    plugins: [referenceLinesPlugin],
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index',
                            intersect: false
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: '#131d3b',
                                titleColor: '#ffffff',
                                bodyColor: '#f1f5f9',
                                borderColor: '#ff4f01',
                                borderWidth: 1,
                                padding: 10,
                                cornerRadius: 6,
                                displayColors: false,
                                callbacks: {
                                    title: function(items) {
                                        if (!items.length) return '';
                                        const idx = items[0].dataIndex;
                                        const s = sortedStudents[idx];
                                        return s ? `${s.name} (${s.regno})` : '';
                                    },
                                    label: function(item) {
                                        const idx = item.dataIndex;
                                        const s = sortedStudents[idx];
                                        if (!s) return '';
                                        if (!s.hasData) {
                                            return [
                                                'Marks: No data',
                                                'Rank: N/A'
                                            ];
                                        }
                                        return [
                                            `Marks: ${s.percentage}%`,
                                            `Rank: #${s.rank}`
                                        ];
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                ticks: {
                                    display: false // Hide per-bar x-axis student names to prevent clutter
                                },
                                grid: {
                                    display: false
                                },
                                title: {
                                    display: true,
                                    text: 'Students (sorted by marks: highest to lowest)',
                                    font: { size: 11, weight: '500' },
                                    color: '#64748b'
                                }
                            },
                            y: {
                                min: 0,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Marks (%)',
                                    font: { weight: 'bold', size: 12 },
                                    color: '#131d3b'
                                },
                                ticks: {
                                    stepSize: 20,
                                    callback: v => v + '%'
                                },
                                grid: {
                                    color: '#e2e8f0',
                                    drawBorder: false
                                }
                            }
                        }
                    }
                });
            }
        }

        // 2. Marks Distribution Pie
        const canvasMPie = document.getElementById('staffMarksPie');
        if (canvasMPie) {
            const ctxMPie = canvasMPie.getContext('2d');
            if (staffMarksPieChart) staffMarksPieChart.destroy();
            staffMarksPieChart = new Chart(ctxMPie, {
                type: 'doughnut',
                data: {
                    labels: ['Passed (>=50%)', 'Failed (<50%)'],
                    datasets: [{
                        data: [data.passed_count || 0, data.failed_count || 0],
                        backgroundColor: ['#047857', '#f43f5e'],
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 15 } }
                    }
                }
            });
        }

    } catch (e) {
        console.error('Error updating staff subject charts:', e);
    }
}

document.addEventListener('DOMContentLoaded', initStaffDashboard);
