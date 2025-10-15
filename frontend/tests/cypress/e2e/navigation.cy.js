describe('RelatAI navigation', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('navigates between primary tabs', () => {
    cy.contains('🚀 Upload Dataset').should('be.visible');
    cy.contains('⚙️ Configure').should('exist');
    cy.viewport('ipad-2');
    cy.percySnapshot('Home - tablet breakpoint');
  });
});
