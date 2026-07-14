from fastcrud import FastCRUD

from .models import AboutUs, BlogPost, Faq, HowToReturn, PrivacyPolicy, TermsAndCondition, WarrantyClaim

crud_about_us: FastCRUD = FastCRUD(AboutUs)
crud_blog_posts: FastCRUD = FastCRUD(BlogPost)
crud_faqs: FastCRUD = FastCRUD(Faq)
crud_how_to_returns: FastCRUD = FastCRUD(HowToReturn)
crud_privacy_policies: FastCRUD = FastCRUD(PrivacyPolicy)
crud_terms_and_conditions: FastCRUD = FastCRUD(TermsAndCondition)
crud_warranty_claims: FastCRUD = FastCRUD(WarrantyClaim)
