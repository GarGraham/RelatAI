Reference Documentation:
Always review Reference-Guide.md before executing actions to understand the codebase better. Always review UserRequirements.md and TechnicalSpecificaiton.md to understand the desired architecture as well. 

Bug Identification:
In the case of code review / exploration bugs shall always be documented in this way:
Clear, concise identification/description of the bug.
The impact of the bug on the application.
Any links to the impacted portion of the code that could also be impacted by a future fix.
Any additional notes or pieces of information that would be helpful to a human or AI attempting to replicate/resolve the bug.

Bug Fixes:
When executing bug fixes the approach shall always include:
A root cause investigation to ensure the cause of the problem is fully understood.
A detailed proposal on how to fix the bug before execution; the plan should prioritize reducing any impacts to the intended use of the application, followed by prioritizing minimal viable patches which limit the risk of new bugs being introduced.
A summary of actions taken to resolve the bug shall be documented.

New Features and Large Refactors:
New features and large refactors shall always include a review of the entire repo before any action is taken.
Upon completion of the review, a detailed plan is required before any code is changed. This plan shall include the purpose of the new feature/refactor, the implementation plan, a risk analysis on impact to existing repo items, and other approaches that were considered but not chosen and why.
New feature code shall always include ample commenting to make code snippets easier to understand for both Human and AI users.

Commit Guidelines:
Prefix commits with type: feat:, fix:, docs:
Documentation Guidelines (Reference-Guide.md):
Any new files created need to be documented in Reference-Guide.md; this file shall include a high level summary of the intended purpose of the file and key features.
Any updates to files require a review of Reference-Guide.md to ensure that if the intended use has changed that the summary and key features are updated. If underlying changes to the app's intended use have occurred TechnicalSpecification.md and UserRequirements.md should be updated accordingly.
