from datetime import datetime, timezone

from src.schemas import ContactInput, ContactOutput, ContactListOutput, ContactOutputData
from src.core.domain import Contact, Profile
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileUpdateNotFoundError,
    ProfileContactNotFoundError,
    ProfileContactValidationError,
)


class AddContactUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, contact: ContactInput) -> ContactOutput:
        if not contact.name or not contact.name.strip():
            raise NewApplicationError(ProfileContactValidationError)

        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)
        if not profile:
            raise NewApplicationError(ProfileUpdateNotFoundError)

        contacts = list(profile.contacts or [])
        now = datetime.now(timezone.utc)
        new_contact = Contact(
            name=contact.name.strip(),
            channel=contact.channel,
            external_id=contact.external_id,
            tags=contact.tags,
            notes=contact.notes,
            created_at=now,
            updated_at=now,
        )
        contacts.append(new_contact)

        await context.repositories.profile.update(
            profile.id,
            Profile(contacts=contacts, updated_at=now),
        )

        return ContactOutput(data=_to_output(new_contact))


class ListContactsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> ContactListOutput:
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)
        if not profile:
            raise NewApplicationError(ProfileUpdateNotFoundError)
        return ContactListOutput(data=[_to_output(contact) for contact in (profile.contacts or [])])


class UpdateContactUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, contact_id: str, contact: ContactInput) -> ContactOutput:
        if not contact.name or not contact.name.strip():
            raise NewApplicationError(ProfileContactValidationError)

        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)
        if not profile:
            raise NewApplicationError(ProfileUpdateNotFoundError)

        contacts = list(profile.contacts or [])
        target = None
        for idx, item in enumerate(contacts):
            if item.id == contact_id:
                target = Contact(
                    _id=item.id,
                    name=contact.name.strip(),
                    channel=contact.channel,
                    external_id=contact.external_id,
                    tags=contact.tags,
                    notes=contact.notes,
                    created_at=item.created_at,
                    updated_at=datetime.now(timezone.utc),
                )
                contacts[idx] = target
                break

        if target is None:
            raise NewApplicationError(ProfileContactNotFoundError)

        await context.repositories.profile.update(
            profile.id,
            Profile(contacts=contacts, updated_at=datetime.now(timezone.utc)),
        )

        return ContactOutput(data=_to_output(target))


class DeleteContactUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, contact_id: str) -> dict:
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)
        if not profile:
            raise NewApplicationError(ProfileUpdateNotFoundError)

        contacts = list(profile.contacts or [])
        remaining = [item for item in contacts if item.id != contact_id]
        if len(remaining) == len(contacts):
            raise NewApplicationError(ProfileContactNotFoundError)

        now = datetime.now(timezone.utc)
        await context.repositories.profile.update(
            profile.id,
            Profile(contacts=remaining, updated_at=now),
        )

        if profile.api_keys:
            for api_key in profile.api_keys:
                if getattr(api_key, "contact_id", None) == contact_id:
                    api_key.is_active = False
            await context.repositories.profile.update_api_keys(user_id, profile.api_keys)

        return {"deleted": True, "id": contact_id}


def _to_output(contact: Contact) -> ContactOutputData:
    return ContactOutputData(
        id=contact.id,
        name=contact.name,
        channel=contact.channel,
        external_id=contact.external_id,
        tags=contact.tags,
        notes=contact.notes,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )
