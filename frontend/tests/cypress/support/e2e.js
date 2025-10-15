import '@percy/cypress';

Cypress.on('uncaught:exception', () => {
  // Prevent Cypress from failing tests on frontend console errors while the
  // prototype evolves. Failures should be asserted explicitly instead.
  return false;
});
