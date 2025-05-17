# Forever Yours RAW Compression Tool: Test Plan

## Table of Contents
- [Introduction](#introduction)
- [Test Environment Setup](#test-environment-setup)
- [Project Queue Test Scenarios](#project-queue-test-scenarios)
  - [Queue Management Tests](#queue-management-tests)
  - [Queue Processing Tests](#queue-processing-tests)
  - [Error Handling Tests](#error-handling-tests)
  - [UI Functionality Tests](#ui-functionality-tests)
- [Verification Points](#verification-points)
- [Test Data Preparation](#test-data-preparation)

## Introduction

This test plan outlines the testing procedures for verifying the functionality, reliability, and usability of the project queue system in the Forever Yours RAW Compression Tool. The test scenarios focus specifically on the queue management, processing capabilities, error handling, and user interface components.

## Test Environment Setup

Before beginning any testing, ensure the following conditions are met:

1. **System Requirements**:
   - Apple Silicon Mac (M1/M2/M3)
   - Python 3.8 or higher
   - FFmpeg installed with VideoToolbox support
   - All required Python packages as listed in the USER_GUIDE.md

2. **Test Data**:
   - Prepare at least 3 sample projects with the standard wedding folder structure
   - Each project should contain at least 5 video files (.mov or .mp4)
   - Ensure some files have varying characteristics (length, resolution, bitrate)

3. **Storage Space**:
   - Ensure sufficient disk space for processing multiple projects simultaneously
   - Recommended at least 3x the total size of all test projects

4. **Application Setup**:
   - Fresh installation or reset of the application
   - Clear any existing queue state from previous tests

## Project Queue Test Scenarios

### Queue Management Tests

#### Test Case 1: Adding Projects to the Queue
1. Launch the application
2. Click "Add Project"
3. Browse and select a project folder
4. Configure project settings
5. Click "Add to Queue"
6. Repeat steps 2-5 to add multiple projects

**Verification Points**:
- Each project appears in the queue table
- Projects are assigned unique IDs
- Projects show "PENDING" status
- Queue statistics update correctly
- Project details are accessible via right-click menu

#### Test Case 2: Reordering Projects in Queue
1. Add at least 3 projects to the queue
2. Select the second project
3. Click "Move Up" to move it to position 1
4. Select the first project
5. Click "Move Down" to move it to position 2
6. Use right-click menu to move another project

**Verification Points**:
- Projects change position as expected
- Project order persists if application is closed and reopened
- Cannot move projects that are currently processing
- UI updates to reflect the new order

#### Test Case 3: Removing Projects from Queue
1. Add at least 2 projects to the queue
2. Select a project
3. Click "Remove Selected"
4. Right-click another project and select "Remove Project"
5. Click "Clear Queue" to remove all projects

**Verification Points**:
- Selected projects are removed from the queue
- Queue statistics update correctly
- Cannot remove a project that is currently processing
- Clear Queue button removes all projects

#### Test Case 4: Editing Projects
1. Add a project to the queue
2. Right-click on the project and select "Edit Project"
3. Modify project settings
4. Save changes

**Verification Points**:
- Project opens in edit mode
- Changes are saved correctly
- Updated project reflects new settings in queue

### Queue Processing Tests

#### Test Case 5: Sequential Processing
1. Add at least 3 projects to the queue
2. Click "Start Queue"
3. Allow all projects to complete

**Verification Points**:
- Projects process one at a time in queue order
- Current project shows "PROCESSING" status
- Completed projects show "COMPLETED" status
- Next project starts automatically when current one finishes
- Progress bars update correctly for both project and queue
- Time elapsed and estimated time remaining display properly

#### Test Case 6: Pausing and Resuming Queue
1. Add at least 2 projects to the queue
2. Click "Start Queue"
3. While processing, click "Pause Queue"
4. Click "Resume Queue"

**Verification Points**:
- Processing stops when paused
- Current project status remains "PROCESSING" while paused
- Processing continues from same point when resumed
- Time elapsed pauses during pause state

#### Test Case 7: Long-Running Queue
1. Add at least 5 projects with large video files to the queue
2. Start the queue and let it run for at least 30 minutes

**Verification Points**:
- Application remains responsive throughout processing
- Projects continue to process sequentially without errors
- Status updates correctly for each project
- Queue state can be saved and restored correctly if application is closed

### Error Handling Tests

#### Test Case 8: Processing Failure Recovery
1. Create a test project with an intentionally corrupted video file
2. Add this project and at least one valid project to the queue
3. Start queue processing

**Verification Points**:
- System detects corrupted file
- Project with corrupted file is marked as "FAILED"
- Queue continues processing next project
- Error details are available in project results
- Failed project can be edited and resubmitted

#### Test Case 9: Canceling Queue Processing
1. Add at least 2 projects to the queue
2. Start queue processing
3. During processing, click "Cancel Queue"

**Verification Points**:
- Processing stops immediately
- Current project is marked as "CANCELED"
- Remaining projects return to "PENDING" status
- Partial results are saved for the canceled project
- Queue can be restarted with pending projects

#### Test Case 10: Handling Application Closure During Processing
1. Add at least 2 projects to the queue
2. Start queue processing
3. While processing, close the application
4. Reopen the application

**Verification Points**:
- Application saves queue state before closing
- On reopening, queue state is restored correctly
- Processing project is reset to "PENDING" status
- Queue can be restarted from where it left off

### UI Functionality Tests

#### Test Case 11: Progress Tracking and Display
1. Add a project with multiple files to the queue
2. Start processing
3. Observe progress indicators during processing

**Verification Points**:
- Project progress bar updates proportionally to completed files
- Queue progress bar updates according to completed projects
- Current project name is displayed correctly
- Time elapsed updates in real-time
- Estimated time remaining updates reasonably

#### Test Case 12: Results Viewing
1. Process at least one project to completion
2. Right-click the completed project and select "View Details"

**Verification Points**:
- Details dialog shows correct project information
- Compression results are displayed (files processed, size reduction)
- Statistics are calculated correctly
- All processed files are listed

## Verification Points

For thorough testing, verify these aspects for each test case:

### Functional Verification
- Feature performs its intended function correctly
- Results match expected outcomes
- System transitions between states correctly

### Data Integrity Verification
- Project information is stored correctly
- Results data is accurate and complete
- Queue state persists between application sessions

### Performance Verification
- System remains responsive during queue processing
- CPU and memory usage stay within reasonable limits
- Processing speed is consistent

### UI Verification
- All elements display correctly
- Status indicators update as expected
- Error messages are clear and helpful

## Test Data Preparation

To effectively test the project queue system, prepare test data sets with these properties:

### Small Test Projects
- 2-3 video files per project
- Short duration videos (30-60 seconds)
- Good for quick verification of basic functionality

### Medium Test Projects
- 5-10 video files per project
- Mix of short and medium duration videos
- Good for general functionality testing

### Large Test Projects
- 15+ video files per project
- Some large files (5+ minutes)
- Good for stress testing and performance validation

### Special Test Cases
- Project with corrupted files
- Project with mixed video formats
- Project with extremely large files
- Project with unusual folder structures