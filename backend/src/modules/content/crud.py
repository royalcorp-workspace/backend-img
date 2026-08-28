from fastcrud import FastCRUD

from .models import AboutUs, BlogPost, Faq, HowToReturn, PrivacyPolicy, TermsAndCondition, WarrantyClaim

crud_about_us: FastCRUD = FastCRUD(AboutUs, is_deleted_column="deleted")
crud_blog_posts: FastCRUD = FastCRUD(BlogPost, is_deleted_column="deleted")
crud_faqs: FastCRUD = FastCRUD(Faq, is_deleted_column="deleted")
crud_how_to_returns: FastCRUD = FastCRUD(HowToReturn, is_deleted_column="deleted")
crud_privacy_policies: FastCRUD = FastCRUD(PrivacyPolicy, is_deleted_column="deleted")
crud_terms_and_conditions: FastCRUD = FastCRUD(TermsAndCondition, is_deleted_column="deleted")
crud_warranty_claims: FastCRUD = FastCRUD(WarrantyClaim, is_deleted_column="deleted")
