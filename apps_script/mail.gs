/**
 * ScreenSmart Google Apps Script integration.
 * Triggers Gmail proposals and schedules interview events in Google Calendar.
 * Ready for Google Apps Script deployment.
 */

/**
 * Sends a professional interview invitation email containing dynamic proposed slots.
 * 
 * @param {string} candidateEmail - The email address of the candidate.
 * @param {string} candidateName - The name of the candidate.
 * @param {string} role - The job title/role.
 * @param {number} score - The candidate's ATS Match score.
 * @param {string} tier - The candidate's fit tier (e.g., "Strong Fit").
 * @param {Array<string>} slots - List of available interview slots.
 * @returns {Object} Result object indicating success or error details.
 */
function sendInterviewProposal(candidateEmail, candidateName, role, score, tier, slots) {
  // Input Validation
  if (!candidateEmail || typeof candidateEmail !== 'string' || !candidateEmail.includes('@')) {
    return { success: false, error: "Invalid candidate email address." };
  }
  if (!candidateName || typeof candidateName !== 'string') {
    return { success: false, error: "Invalid candidate name." };
  }
  if (!role || typeof role !== 'string') {
    return { success: false, error: "Invalid job role." };
  }
  if (!slots || !Array.isArray(slots) || slots.length === 0) {
    return { success: false, error: "Interview slots must be a non-empty array." };
  }

  try {
    var subject = "Interview Invitation: " + role + " - ScreenSmart Recruitment";
    
    var body = "Dear " + candidateName + ",\n\n" +
               "Thank you for your application for the " + role + " position. " +
               "Our AI screening system analyzed your profile and ranked you as a " + tier + 
               " with an ATS Match Score of " + score + "%.\n\n" +
               "We would love to invite you for an interview. Please reply to this email " +
               "confirming your preference from the following available slots:\n\n" +
               slots.map(function(slot) { return "📅 " + slot; }).join("\n") + "\n\n" +
               "Once we receive your response, we will send a calendar event containing the video meeting link.\n\n" +
               "Best regards,\n" +
               "Recruitment Team\n" +
               "ScreenSmart Suite";

    MailApp.sendEmail({
      to: candidateEmail,
      subject: subject,
      body: body
    });

    Logger.log("Interview proposal sent successfully to: " + candidateEmail);
    return { success: true, message: "Email proposal sent successfully to " + candidateEmail };
  } catch (error) {
    Logger.log("Error in sendInterviewProposal: " + error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Automatically creates a Google Calendar event for the scheduled slot.
 * 
 * @param {string} candidateEmail - The email address of the candidate.
 * @param {string} candidateName - The name of the candidate.
 * @param {string} role - The job title/role.
 * @param {string} dateTimeString - Date and time string parseable by the Date constructor.
 * @returns {Object} Result object containing success state and event ID.
 */
function createInterviewEvent(candidateEmail, candidateName, role, dateTimeString) {
  // Input Validation
  if (!candidateEmail || typeof candidateEmail !== 'string' || !candidateEmail.includes('@')) {
    return { success: false, error: "Invalid candidate email address." };
  }
  if (!candidateName || typeof candidateName !== 'string') {
    return { success: false, error: "Invalid candidate name." };
  }
  if (!role || typeof role !== 'string') {
    return { success: false, error: "Invalid job role." };
  }
  if (!dateTimeString) {
    return { success: false, error: "Invalid date-time string." };
  }

  try {
    var calendar = CalendarApp.getDefaultCalendar();
    if (!calendar) {
      return { success: false, error: "Could not access default Google Calendar." };
    }

    var title = "Interview: " + candidateName + " - " + role;
    
    // Parse date/time string
    var startTime = new Date(dateTimeString);
    if (isNaN(startTime.getTime())) {
      return { success: false, error: "Unable to parse date-time string: " + dateTimeString };
    }

    // Set duration to 1 hour
    var endTime = new Date(startTime.getTime() + 60 * 60 * 1000); 

    var event = calendar.createEvent(title, startTime, endTime, {
      guests: candidateEmail,
      sendInvites: true,
      description: "ScreenSmart automated interview schedule.\n" +
                   "Position: " + role + "\n" +
                   "Candidate: " + candidateName + " (" + candidateEmail + ")\n" +
                   "Meeting Link: https://meet.google.com/abc-defg-hij"
    });

    Logger.log("Calendar Event created successfully with ID: " + event.getId());
    return { success: true, eventId: event.getId(), message: "Event scheduled successfully." };
  } catch (error) {
    Logger.log("Error in createCalendarEvent: " + error.toString());
    return { success: false, error: error.toString() };
  }
}
